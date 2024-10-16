# Nico: 这个__init__.py里面不要放太杂的东西，只有一些关于插件的最基础的信息，以及类的注册和解除注册代码
# 其它代码写到其它py文件中然后导入过来。
# 导入包要在包名之前加.  不然Blender无法识别。
import bpy.props

# DBMT插件面板
from .mmt_panel.panel_ui import *

# 右键菜单
from .mmt_rightclick_menu.mesh_operator import *

# 全新动画Mod支持(开发中)
from .mmt_animation.animation_operator import *

# 基于Buffer的全新格式
from .buffer_io.buffer_import import *

# 插件基础信息
bl_info = {
    "name": "DBMT-Blender-Plugin",
    "description": "DBMT的Blender插件 目前只支持3.6LTS版本",
    "blender": (3, 6, 0),
    "version": (1, 0, 0, 4),
    "location": "View3D",
    "category": "Generic"
}


# 需要注册和取消注册的所有类
register_classes = (
    # migoto
    MMTPathProperties,
    MMTPathOperator,
    MMTPanel,

    # 3Dmigoto ib和vb格式导入导出
    Import3DMigotoRaw,
    Export3DMigoto,

    # 新的Buffer格式导入导出
    Import_DBMT_Buffer,

    # MMT的一键快速导入导出
    MMTImportAllVbModel,
    MMTExportAllIBVBModel,

    # mesh_operator 右键菜单栏
    RemoveUnusedVertexGroupOperator,
    MergeVertexGroupsWithSameNumber,
    FillVertexGroupGaps,
    AddBoneFromVertexGroup,
    RemoveNotNumberVertexGroup,
    ConvertToFragmentOperator,
    MMTDeleteLoose,
    MMTResetRotation,
    MigotoRightClickMenu,
    MMTCancelAutoSmooth,
    MMTShowIndexedVertices,
    MMTSetAutoSmooth89,
    SplitMeshByCommonVertexGroup,

    # MMD类型动画Mod支持
    MMDModIniGenerator
)


def register():
    # 注册所有类
    for cls in register_classes:
        bpy.utils.register_class(cls)

    # 新建一个属性用来专门装MMT的路径
    bpy.types.Scene.mmt_props = bpy.props.PointerProperty(type=MMTPathProperties)

    # MMT数值保存的变量
    bpy.types.Scene.mmt_mmd_animation_mod_start_frame = bpy.props.IntProperty(name="Start Frame")
    bpy.types.Scene.mmt_mmd_animation_mod_end_frame = bpy.props.IntProperty(name="End Frame")
    bpy.types.Scene.mmt_mmd_animation_mod_play_speed = bpy.props.FloatProperty(name="Play Speed")

    # 右键菜单
    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func_migoto_right_click)

    # 在Blender退出前保存选择的MMT的路径
    bpy.app.handlers.depsgraph_update_post.append(save_mmt_path)

    
def unregister():
    # 取消注册所有类
    for cls in reversed(register_classes):
        bpy.utils.unregister_class(cls)

    # 退出时移除MMT路径变量
    del bpy.types.Scene.mmt_props

    # 退出时移除右键菜单
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func_migoto_right_click)

    # 退出注册时删除MMT的MMD变量
    del bpy.types.Scene.mmt_mmd_animation_mod_start_frame
    del bpy.types.Scene.mmt_mmd_animation_mod_end_frame
    del bpy.types.Scene.mmt_mmd_animation_mod_play_speed


