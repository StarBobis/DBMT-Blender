import os

from .buffer_format import *

from bpy.types import StringProperty,CollectionProperty,BoolProperty
from bpy_extras.io_utils import ImportHelper


def read_buffer_and_combine_obj_list(format_json_path:str) -> list:
    obj_result = []

    return obj_result


class Import_DBMT_Buffer(bpy.types.Operator, ImportHelper):
    bl_idname = "import_mesh.dbmt_buffer"
    bl_label = "导入DBMT原始Buffer文件"
    bl_options = {'UNDO'}

    filename_ext = 'json'
    filter_glob: StringProperty(
        default='*.json',
        options={'HIDDEN'},
    ) # type: ignore

    files: CollectionProperty(
        name="文件路径",
        type=bpy.types.OperatorFileListElement,
    ) # type: ignore

    # 这里flip_texcoord_v是因为我们游戏里Dump出来的图片是逆向的，所以这里要flip一下才能对上
    # 理论上可以去掉，设为总是flip对吗？
    flip_texcoord_v: BoolProperty(
        name="Flip TEXCOORD V",
        description="Flip TEXCOORD V asix during importing",
        default=True,
    ) # type: ignore

    def execute(self, context):
        # 创建一个集合，名称为导入的文件夹的名称
        collection_name = os.path.basename(os.path.dirname(self.file_path))
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

        # 解析并读取Buffer文件中的数据，返回一个obj对象

        obj_results = read_buffer_and_combine_obj_list(self.file_path)

        for obj in obj_results:
            # TODO 测试一下这里为什么不直接link而是要复制一份呢？
            new_object = obj.copy()
            new_object.data = obj.data.copy()
            collection.objects.link(new_object)
            bpy.data.objects.remove(obj)
            

            # collection.objects.link(obj)

            

        
        


        return {'FINISHED'}
    