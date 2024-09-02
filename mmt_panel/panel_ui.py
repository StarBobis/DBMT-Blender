import os
import bpy
import json

from .panel_functions import *

from ..migoto.migoto_export import *
from ..migoto.migoto_import import *


class MMTPathProperties(bpy.types.PropertyGroup):
    path: bpy.props.StringProperty(
        name="主路径",
        description="选择DBMT的主路径",
        default=load_path(),
        subtype='DIR_PATH'
    ) # type: ignore

    export_same_number: bpy.props.BoolProperty(
        name="My Checkbox",
        description="This is a checkbox in the sidebar",
        default=False
    ) # type: ignore

    def __init__(self) -> None:
        super().__init__()
        self.subtype = 'DIR_PATH'
        self.path = load_path()


class MMTPathOperator(bpy.types.Operator):
    bl_idname = "mmt.select_folder"
    bl_label = "Select Folder"

    def execute(self, context):
        # 在这里处理文件夹选择逻辑
        bpy.ops.ui.directory_dialog('INVOKE_DEFAULT', directory=context.scene.mmt_props.path)
        return {'FINISHED'}


# MMT的侧边栏
class MMTPanel(bpy.types.Panel):
    bl_label = "DBMT插件 " 
    bl_idname = "VIEW3D_PT_DBMT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'DBMT'

    def draw(self, context):
        layout = self.layout
        row = layout.row()

        props = context.scene.mmt_props
        layout.prop(props, "path")

        # 获取DBMT.exe的路径
        mmt_path = os.path.join(context.scene.mmt_props.path, "DBMT-GUI.exe")
        mmt_location = os.path.dirname(mmt_path)
        if not os.path.exists(mmt_path):
            layout.label(text="错误:请选择DBMT主路径 ", icon='ERROR')

        # 读取MainSetting.json中当前游戏名称
        current_game = ""
        main_setting_path = os.path.join(context.scene.mmt_props.path, "Configs\\Main.json")
        if os.path.exists(main_setting_path):
            main_setting_file = open(main_setting_path)
            main_setting_json = json.load(main_setting_file)
            main_setting_file.close()
            current_game = main_setting_json["GameName"]
            layout.label(text="当前游戏: " + current_game)
        else:
            layout.label(text="错误:请选择DBMT主路径 ", icon='ERROR')

        # 根据当前游戏名称，读取GameSetting中的OutputFolder路径并设置
        output_folder_path = mmt_location + "\\Games\\" + current_game + "\\3Dmigoto\\Mods\\output\\"

        # 绘制一个CheckBox用来存储是否导出相同顶点数
        layout.separator()
        layout.prop(context.scene.mmt_props, "export_same_number", text="导出不改变顶点数")

        # 分隔符
        layout.separator()
        layout.label(text="在OutputFolder中导入或导出")

        # 手动导入buf文件
        operator_import_ib_vb = self.layout.operator("import_mesh.migoto_raw_buffers_mmt", text="导入 .ib & .vb 模型文件")
        operator_import_ib_vb.filepath = output_folder_path

        # 手动导出同理，点这个之后默认路径为OutputFolder，这样直接就能去导出不用翻很久文件夹找路径了
        operator_export_ibvb = self.layout.operator("export_mesh.migoto_mmt", text="导出 .ib & .vb 模型文件")
        operator_export_ibvb.filepath = output_folder_path + "1.vb"

        # 添加分隔符
        layout.separator()

        # 一键快速导入
        layout.label(text="在OutputFolder中一键导入导出")
        operator_fast_import = self.layout.operator("mmt.import_all", text="一键导入所有.ib & .vb模型文件")

        # 一键快速导出当前选中Collection中的所有model到对应的hash值文件夹中，并直接调用MMT.exe的Mod生成方法，做到导出完即可游戏里F10刷新看效果。
        operator_export_ibvb = self.layout.operator("mmt.export_all", text="一键导出选中的MMT集合")

        # 添加分隔符
        layout.separator()

        # TODO 导出MMD的Bone Matrix，连续骨骼变换矩阵，并生成ini文件
        # TODO 重构完成Blender插件后开发此技术
        layout.label(text="骨骼蒙皮动画Mod")
        layout.prop(context.scene, "mmt_mmd_animation_mod_start_frame")
        layout.prop(context.scene, "mmt_mmd_animation_mod_end_frame")
        layout.prop(context.scene, "mmt_mmd_animation_mod_play_speed")
        operator_export_mmd_bone_matrix = layout.operator("mmt.export_mmd_animation_mod", text="Export Animation Mod")
        operator_export_mmd_bone_matrix.output_folder = output_folder_path

        # # 添加分隔符
        # layout.separator()
        #
        # # 将当前动画的每一帧都转换为一个Position.buf然后导出，并生成逐帧ini文件
        # row = layout.row()
        # row.label(text="FrameBased Animation Mod")
        # operator_export_mmd_bone_matrix = row.operator("export_mesh.migoto", text="Export Position Files")
        # row = layout.row()
        # row.prop(context.scene, "mmt_mmd_animation_mod_start_frame")
        # row.prop(context.scene, "mmt_mmd_animation_mod_end_frame")
        # row.prop(context.scene, "mmt_mmd_animation_mod_play_speed")
        # # 添加分隔符
        # layout.separator()
        #
        # # 一键快速导入所有位于OutputFolder下的.txt模型
        # layout.label(text="ShapeKey Mod")

        