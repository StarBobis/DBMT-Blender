# 导入其它文件依赖
from .buffer_format import *

# 导入用到的包
import os
import json
from enum import Enum

# 导入bpy相关属性
from bpy.props import StringProperty,CollectionProperty,BoolProperty
from bpy_extras.io_utils import ImportHelper

class DXGI_FORMAT(Enum):
    DXGI_FORMAT_R16_UINT:str = "DXGI_FORMAT_R16_UINT"
    DXGI_FORMAT_R32_UINT:str = "DXGI_FORMAT_R32_UINT"


def read_buffer_and_combine_obj_list(format_json_path:str) -> list:
    # 读取 JSON 文件
    with open(format_json_path, 'r') as file:
        format_json_data = json.load(file)

    dir_path = os.path.dirname(format_json_path)
    '''
    TODO
    读取每个IndexBuffer文件和VertexBuffer文件。
    最后组装成一个obj文件列表返回即可，因为这里还要进行分割呢，挺有意思的。
    而且还要给个单独的设置来兼容CPU-PreSkinning的部分。

    TODO 
    遇到困难不要怕，我们把困难拆分为一个一个简单的步骤来逐个解决：
    1.需要一个IndexBuffer的类，填入路径进行初始化
    2.IndexBuffer类需要具有SelfDivide功能，所以提取出的Format.json中要记录first_index和index_count
    3.是否可以根据first_index的插值推断出每个index_count的大小？如果可以的话就不用记录index_count了，不然还要改程序有点麻烦。
    
    '''
    

    # 访问 IndexBufferList
    index_buffer_list = format_json_data.get("IndexBufferList", [])
    for index_buffer in index_buffer_list:
        index_buffer_file_name = index_buffer.get("FileName")
        index_buffer_format = index_buffer.get("Format")

        index_buffer_file_path = os.path.join(dir_path, index_buffer_file_name)

        index_buffer_data_list = []
        if DXGI_FORMAT.DXGI_FORMAT_R32_UINT == index_buffer_format:
            index_buffer_data_list = BufferReader.read_index_buffer(index_buffer_file_path,4)
        elif DXGI_FORMAT.DXGI_FORMAT_R16_UINT == index_buffer_format:
            index_buffer_data_list = BufferReader.read_index_buffer(index_buffer_file_path,2)

        
        

        print("Index Buffer FileName:", index_buffer.get("FileName"))
        print("Format:", index_buffer.get("Format"))
        print("Order Number:", index_buffer.get("OrderNumber"))

    # 访问 VertexBufferList
    vertex_buffer_list = format_json_data.get("VertexBufferList", [])
    for vertex_buffer in vertex_buffer_list:
        print("\nVertex Buffer FileName:", vertex_buffer.get("FileName"))
        element_list = vertex_buffer.get("ElementList", [])
        for element in element_list:
            print("  Format:", element.get("Format"))
            print("  Input Slot Class:", element.get("InputSlotClass"))
            print("  Order Number:", element.get("OrderNumber"))
            print("  Semantic Index:", element.get("SemanticIndex"))
            print("  Semantic Name:", element.get("SemanticName"))

    obj_result = []

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
            obj_results = read_buffer_and_combine_obj_list(json_file_path)

            # 遍历每一个obj对象，并链接到集合中
            for obj in obj_results:
                # 因为之前导入的过程中可能已经链接到scene了，所以必选在这里先断开链接否则会出现两个实例
                bpy.context.scene.collection.objects.unlink(obj)
                # 再链接到集合，就能显示在集合下面了
                collection.objects.link(obj)

        return {'FINISHED'}
    

    