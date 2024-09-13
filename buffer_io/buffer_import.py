# 导入其它文件依赖
from .buffer_format import *
from .buffer_utils import *

# 导入用到的包
import os
import json
from enum import Enum

# 导入bpy相关属性
from bpy.props import StringProperty,CollectionProperty,BoolProperty
from bpy_extras.io_utils import ImportHelper
from bpy_extras.io_utils import unpack_list, ImportHelper, axis_conversion
from bpy_extras.io_utils import orientation_helper



# 这里第一个参数传递operator的目的是为了能够输出错误到Blender Console
def read_buffer_and_combine_obj(operator,format_json_path:str):
    # 读取 JSON 文件
    with open(format_json_path, 'r') as file:
        format_json_data = json.load(file)

    # 读取文件名用于设置mesh名称
    file_name = os.path.basename(format_json_path)
    draw_ib = file_name.split("-")[0]

    # 初始化读取的文件的目录，用于后续拼接完整文件路径
    dir_path = os.path.dirname(format_json_path)
    buffer_list = format_json_data.get("BufferList", [])

    # 读取IndexBuffer列表
    DATA_INDEX_LIST = []
    for buffer in buffer_list:
        buffer_element_name = str(buffer.get("ElementName"))
        if buffer_element_name.startswith("Index"):
            # 读取基础属性
            buffer_file_name = str(buffer.get("FileName"))
            buffer_format = str(buffer.get("Format"))
            # 拼接文件完整路径
            buffer_file_path = os.path.join(dir_path, buffer_file_name)

            DATA_INDEX = read_formated_data(buffer_file_path, buffer_format)
            DATA_INDEX_LIST.append(DATA_INDEX)

    if len(DATA_INDEX_LIST) == 0:
        operator.report({'ERROR'}, "无法读取到任何Index数据，请检查是否正确提取")

    # 读取BufferList
    for buffer in buffer_list:
        # 读取基础属性
        buffer_file_name = str(buffer.get("FileName"))
        buffer_format = str(buffer.get("Format"))
        buffer_element_name = str(buffer.get("ElementName"))
        # 拼接文件完整路径
        buffer_file_path = os.path.join(dir_path, buffer_file_name)

        # 根据元素名称调用对应的读取方法，把导入的元素进行拼接赋值到obj
        if "POSITION" == buffer_element_name:
            DATA_POSITION = read_formated_data(buffer_file_path, buffer_format)
        elif "NORMAL" == buffer_element_name:
            pass
        elif "TANGENT" == buffer_element_name:
            pass
        elif buffer_element_name.startswith("COLOR"):
            pass
        elif buffer_element_name.startswith("TEXCOORD"):
            pass
        elif buffer_element_name.startswith("BLENDWEIGHT"):
            pass
        elif buffer_element_name.startswith("BLENDINDICES"):
            pass
        elif buffer_element_name.startswith("Index"):
            pass
        
    # 开始拼接obj并返回
    obj_result = []

    partname = 0

    for INDEX_DATA in DATA_INDEX_LIST:
        # 创建mesh和Object对象，用于后续填充
        mesh = bpy.data.meshes.new(draw_ib + "-" +str(partname))
        obj = bpy.data.objects.new(mesh.name, mesh)

        # 设置坐标系
        global_matrix = axis_conversion(from_forward='-Z', from_up='Y').to_4x4()
        obj.matrix_world = global_matrix

        # 导入基础mesh数据，也就是Index + POSITION
        if len(DATA_POSITION) == 0:
            operator.report({'ERROR'}, "无法读取到POSITION数据")
        else:
            index_count = int(len(INDEX_DATA)) 
            faces = [(INDEX_DATA[j], INDEX_DATA[j+1], INDEX_DATA[j+2]) for j in range(0, index_count - 2, 3)]
            mesh.from_pydata(DATA_POSITION, [], faces)

        # TODO 导入其它数据


        # 全部属性设置完成后进行validate
        mesh.validate(verbose=False, clean_customdata=False)  # *Very* important to not remove lnors here!
        mesh.update()
        
        # 添加到用于返回的集合中
        obj_result.append(obj)
        # 自增1用来区别每个obj
        partname = partname + 1
    return obj_result



class Import_DBMT_Buffer(bpy.types.Operator, ImportHelper):
    bl_idname = "import_mesh.dbmt_buffer"
    bl_label = "导入DBMT原始Buffer文件"
    bl_options = {'UNDO'}

    filename_ext = '.json'
    filter_glob : StringProperty(default='*.json', options={'HIDDEN'})  # type: ignore
    files: CollectionProperty(name="File Path", type=bpy.types.OperatorFileListElement, ) # type: ignore
    flip_texcoord_v: BoolProperty(name="Flip TEXCOORD V", description="Flip TEXCOORD V asix during importing", default=True,) # type: ignore

    def execute(self, context):
        # 因为ImportHelper会可以选择多个文件，self.filepath总是会获取最后一个文件的路径，这样我们通过os.path.dirname()就可以获取到它的目录了
        # self.report({'INFO'}, "Self.FilePath: " + self.filepath)
        # Self.FilePath: C:\Users\Administrator\Desktop\DBMT\Games\HI3_NEW\3Dmigoto\Mods\output\7b4e1855\7b4e1855-HI3_GPU_T01.json
        dirpath = os.path.dirname(self.filepath)

        # 获取导入的目录的文件夹名称
        collection_name = os.path.basename(dirpath)

        # 创建一个集合
        collection = bpy.data.collections.new(collection_name)

        # 把集合链接到当前场景上
        bpy.context.scene.collection.children.link(collection)
        # self.report({'INFO'}, "Import " + filename.name)

        for filename in self.files:
            # 根据之前获取的目录，我们这里就可以根据获取每个文件的路径了，因为在VSCode里是没有filename.之后的智能提示的，这样获取比较安全
            json_file_path = os.path.join(dirpath, filename.name)
            
            # 解析并读取Buffer文件中的数据，返回一个obj对象
            obj_results = read_buffer_and_combine_obj(self,json_file_path)

            # 遍历每一个obj对象，并链接到集合中
            for obj in obj_results:
                # 因为之前导入的过程中可能已经链接到scene了，所以必选在这里先断开链接否则会出现两个实例
                # bpy.context.scene.collection.objects.unlink(obj)
                # 再链接到集合，就能显示在集合下面了
                collection.objects.link(obj)

        return {'FINISHED'}
    

    