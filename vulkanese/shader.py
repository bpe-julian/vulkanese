import json
from vutil import *
import os
here = os.path.dirname(os.path.abspath(__file__))
from vulkan import *
from buffer import *
from pathlib import Path

class Shader(PrintClass):
	def __init__(self, pipeline, setupDict):
		PrintClass.__init__(self)
		self.vkDevice = pipeline.device.vkDevice
		self.setupDict = setupDict
		self.outputWidthPixels  = setupDict["outputWidthPixels"]
		self.outputHeightPixels = setupDict["outputHeightPixels"]
		
		print("creating shader with description")
		print(json.dumps(setupDict, indent=4))

		# attributes are ex. location, normal, color
		self.buffers    = []
		
		# apply template if shader is not precompiled
		if setupDict["path"].endswith("template"):
			with open(setupDict["path"], 'r') as f:
				shader_spirv = f.read()
			
			# novel INPUT buffers belong to THIS shader (others are linked)
			for bufferDict in setupDict["inBuffers"]:
				existsAlready = False
				shader_spirv  = shader_spirv.replace("LOCATION_" + bufferDict["name"], str(bufferDict["location"]))
				for b in pipeline.getAllBuffers():
					if bufferDict["name"] == b.setupDict["name"]:
						existsAlready = True
				
				if not existsAlready:
					newBuffer     = Buffer(pipeline.device, bufferDict)
					self.buffers  += [newBuffer]
					self.children += [newBuffer]
						
					
			# ALL the OUTPUT buffers are owned by THIS shader
			for bufferDict in setupDict["outBuffers"]:
				print("adding outbuff " + bufferDict["name"])
				shader_spirv  = shader_spirv.replace("LOCATION_" + bufferDict["name"], str(bufferDict["location"]))
				newBuffer     = Buffer(pipeline.device, bufferDict)
				self.buffers  += [newBuffer]
				self.children += [newBuffer]
					
			print("---final shader code---")
			print(shader_spirv)
			print("--- end shader code ---")
			
			print("compiling shader")
			compShadersPath = os.path.join(here, "compiledShaders")
			compShadersPath = "compiledShaders"
			Path(compShadersPath).mkdir(parents=True, exist_ok=True)
			basename = os.path.basename(setupDict["path"])
			outfilename = os.path.join(compShadersPath, basename.replace(".template", ""))
			with open(outfilename, 'w+') as f:
				f.write(shader_spirv)
			
			os.system("glslc " + outfilename)
			# POS always outputs to "a.spv"
			with open("a.spv", 'rb') as f:
				shader_spirv = f.read()
			
		else:
			self.path = os.path.join(here, setupDict["path"])
			with open(self.path, 'rb') as f:
				shader_spirv = f.read()
			

		# Create shader
		self.shader_create = VkShaderModuleCreateInfo(
			sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
			flags=0,
			codeSize=len(shader_spirv),
			pCode=shader_spirv
		)

		self.vkShader = vkCreateShaderModule(self.vkDevice, self.shader_create, None)
		
		# Create shader stage
		self.shader_stage_create = VkPipelineShaderStageCreateInfo(
			sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
			stage=eval(setupDict["stage"]),
			module=self.vkShader,
			flags=0,
			pSpecializationInfo=None,
			pName='main')
		
		
	def release(self):
		print("destroying shader")
		PrintClass.release(self)
		vkDestroyShaderModule(self.vkDevice, self.vkShader, None)
		