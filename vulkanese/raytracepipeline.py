import ctypes
import os
import time
import json
from vulkan import *
from surface import *
from stage import *
from renderpass import *
from pipelines import *
from commandbuffer import *
from vutil import *
from vulkanese import *
from PIL import Image as pilImage

here = os.path.dirname(os.path.abspath(__file__))
def getVulkanesePath():
	return here

from enum import Enum
class StageIndices(Enum):
	eRaygen           = 0
	eMiss             = 1
	eMiss2            = 2
	eClosestHit       = 3
	eShaderGroupCount = 4
	
class RaytracePipeline(Pipeline):
	def __init__(self, device, setupDict):
		Pipeline.__init__(self, device, setupDict)
		self.stages = [s.shaderStageCreateInfo for s in self.stageDict.values()]
		for stageName, stage in self.stageDict.items():
			stage.createStridedRegion()
			
		# Shader groups
		self.shaderGroupCreateInfo = VkRayTracingShaderGroupCreateInfoKHR(
			sType = VK_STRUCTURE_TYPE_RAY_TRACING_SHADER_GROUP_CREATE_INFO_KHR,
			pNext = None,
			type  = VK_RAY_TRACING_SHADER_GROUP_TYPE_GENERAL_KHR,
			generalShader      = VK_SHADER_UNUSED_KHR,
			closestHitShader   = VK_SHADER_UNUSED_KHR,
			anyHitShader       = VK_SHADER_UNUSED_KHR,
			intersectionShader = VK_SHADER_UNUSED_KHR,
			pShaderGroupCaptureReplayHandle = None
			)
		rtShaderGroups = [self.shaderGroupCreateInfo]
		# Push constant: we want to be able to update constants used by the shaders
		#pushConstant = vkPushConstantRange(
		#	VK_SHADER_STAGE_RAYGEN_BIT_KHR | VK_SHADER_STAGE_CLOSEST_HIT_BIT_KHR | VK_SHADER_STAGE_MISS_BIT_KHR,
		#	0, sizeof(PushConstantRay)};
		#VkPipelineLayoutCreateInfo pipelineLayoutCreateInfo{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
		#pipelineLayoutCreateInfo.pushConstantRangeCount = 1;
		#.pPushConstantRanges    = &pushConstant;
	
		self.sbt = ShaderBindingTable(self)

		# Assemble the shader stages and recursion depth info into the ray tracing pipeline
		# In this case, self.rtShaderGroups.size() == 4: we have one raygen group,
		# two miss shader groups, and one hit group.
		# The ray tracing process can shoot rays from the camera, and a shadow ray can be shot from the
		# hit points of the camera rays, hence a recursion level of 2. This number should be kept as low
		# as possible for performance reasons. Even recursive ray tracing should be flattened into a loop
		# in the ray generation to avoid deep recursion.
		self.rayPipelineInfo = VkRayTracingPipelineCreateInfoKHR(
			sType = VK_STRUCTURE_TYPE_RAY_TRACING_PIPELINE_CREATE_INFO_KHR,
			pNext      = None, 
			flags      = 0,
			stageCount = len(self.stages),  # Stages are shaders
			pStages    = [self.stages],
			groupCount = len(rtShaderGroups),
			pGroups    = rtShaderGroups,
			maxPipelineRayRecursionDepth = 2, # Ray depth
			layout               = self.pipelineLayout
			)

		self.vkPipeline = vkCreateRayTracingPipelinesKHR(
			device = self.vkDevice,
			deferredOperation = None, 
			pipelineCache = None, 
			createInfoCount = 1,
			pCreateInfos = [self.rayPipelineInfo],
			pAllocator = None
		)
		
class ShaderBindingTable(Sinode):
	def __init__(self, pipeline):
		Sinode.__init__(self, pipeline)
		self.pipeline = pipeline
		self.pipelineDict = pipeline.setupDict
		self.vkCommandPool  = pipeline.device.vkCommandPool
		self.device       = pipeline.device
		self.vkDevice     = pipeline.device.vkDevice
		self.outputWidthPixels  = self.pipelineDict["outputWidthPixels"]
		self.outputHeightPixels = self.pipelineDict["outputHeightPixels"]
		self.commandBufferCount = 0
		
		missCount = 2
		hitCount  = 1
		handleCount = 1 + missCount + hitCount
		self.allStages = self.pipeline.stageDict.values()
		
		self.raygenShaderBindingTableStride   = 0
		self.raygenShaderBindingTableSize     = 0
		self.callableShaderBindingTableSize   = 0
		self.callableShaderBindingTableStride = 0
		self.missShaderBindingTableSize       = 0
		self.missShaderBindingTableStride     = 0
		self.hitShaderBindingTableSize        = 0
		self.hitShaderBindingTableStride      = 0
		
		for stage in self.allStages:
			print(stage)
			if stage.stage == VK_SHADER_STAGE_RAYGEN_BIT_KHR:
				self.raygenShaderBindingTableSize   += stage.size
				self.raygenShaderBindingTableStride  = max(self.raygenShaderBindingTableStride, stage.stride)
		
			if stage.stage == VK_SHADER_STAGE_CALLABLE_BIT_KHR:
				self.callableShaderBindingTableSize   += stage.size
				self.callableShaderBindingTableStride  = max(self.callableShaderBindingTableStride, stage.stride)
		
			if stage.stage == VK_SHADER_STAGE_MISS_BIT_KHR:
				self.missShaderBindingTableSize   += stage.size
				self.missShaderBindingTableStride  = max(self.missShaderBindingTableStride, stage.stride)
		
			if stage.stage == VK_SHADER_STAGE_CLOSEST_HIT_BIT_KHR:
				self.hitShaderBindingTableSize   += stage.size
				self.hitShaderBindingTableStride  = max(self.callableShaderBindingTableStride, stage.stride)
		
		# Get the shader group handles
		result = vkGetRayTracingShaderGroupHandlesKHR(self.vkDevice, self.rtPipeline, 0, handleCount, dataSize, handles.data());
		assert(result == VK_SUCCESS)

		# Allocate a buffer for storing the SBT.
		sbtSize = self.rgenRegion.size + self.missRegion.size + self.hitRegion.size + self.callRegion.size;
		self.rtSBTBuffer = \
		Buffer(sbtSize,
			VK_BUFFER_USAGE_TRANSFER_SRC_BIT | 
			VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT | VK_BUFFER_USAGE_SHADER_BINDING_TABLE_BIT_KHR,
			VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | 
			VK_MEMORY_PROPERTY_HOST_COHERENT_BIT
		);
	def createStridedRegion(self):

		deviceAddress = vkGetBufferDeviceAddress(
			self.vkDevice, 
			buffer.vkBufferDeviceAddressInfo
		)
		
		self.vkStridedDeviceAddressRegion = \
		VkStridedDeviceAddressRegionKHR(
			deviceAddress = deviceAddress,
			stride        = self.setupDict["stride"],
			size          = self.setupDict["SIZEBYTES"]
		)