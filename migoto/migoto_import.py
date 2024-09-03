from .migoto_format import *
from array import array
from glob import glob

import os.path
import itertools
import bpy
import json

from bpy_extras.io_utils import unpack_list, ImportHelper, axis_conversion
from bpy.props import BoolProperty, StringProperty, CollectionProperty
from bpy_extras.io_utils import orientation_helper


def import_vertex_groups(mesh, obj, blend_indices, blend_weights):
    assert (len(blend_indices) == len(blend_weights))
    if blend_indices:
        # We will need to make sure we re-export the same blend indices later -
        # that they haven't been renumbered. Not positive whether it is better
        # to use the vertex group index, vertex group name or attach some extra
        # data. Make sure the indices and names match:
        num_vertex_groups = max(itertools.chain(*itertools.chain(*blend_indices.values()))) + 1
        for i in range(num_vertex_groups):
            obj.vertex_groups.new(name=str(i))
        for vertex in mesh.vertices:
            for semantic_index in sorted(blend_indices.keys()):
                for i, w in zip(blend_indices[semantic_index][vertex.index],
                                blend_weights[semantic_index][vertex.index]):
                    if w == 0.0:
                        continue
                    obj.vertex_groups[i].add((vertex.index,), w, 'REPLACE')


def import_uv_layers(mesh, obj, texcoords, flip_texcoord_v):
    for (texcoord, data) in sorted(texcoords.items()):
        '''
        TODO 这里他说的TEXCOORD可以有四个分量的原因是什么？是不是因为自定义数据写到TEXCOORD里的原因？
        如果是因为自定义数据，则自定义数据应该由其它模块处理

        TEXCOORDS can have up to four components, but UVs can only have two
        dimensions. Not positive of the best way to handle this in general,
        but for now I'm thinking that splitting the TEXCOORD into two sets of
        UV coordinates might work:
        '''
        dim = len(data[0])
        if dim == 4:
            components_list = ('xy', 'zw')
        elif dim == 2:
            components_list = ('xy',)
        else:
            raise Fatal('Unhandled TEXCOORD dimension: %i' % dim)
        cmap = {'x': 0, 'y': 1, 'z': 2, 'w': 3}

        for components in components_list:
            uv_name = 'TEXCOORD%s.%s' % (texcoord and texcoord or '', components)
            if hasattr(mesh, 'uv_textures'):  # 2.79
                mesh.uv_textures.new(uv_name)
            else:  # 2.80
                mesh.uv_layers.new(name=uv_name)
            blender_uvs = mesh.uv_layers[uv_name]

            # Can't find an easy way to flip the display of V in Blender, so
            # add an option to flip it on import & export:
            if flip_texcoord_v:
                flip_uv = lambda uv: (uv[0], 1.0 - uv[1])
                # Record that V was flipped, so we know to undo it when exporting:
                obj['3DMigoto:' + uv_name] = {'flip_v': True}
            else:
                flip_uv = lambda uv: uv

            # TODO 这种全写在一行里的太难理解了
            uvs = [[d[cmap[c]] for c in components] for d in data]

            for l in mesh.loops:
                blender_uvs.data[l.index].uv = flip_uv(uvs[l.vertex_index])


def import_faces_from_ib(mesh, ib):
    mesh.loops.add(len(ib.faces) * 3)
    mesh.polygons.add(len(ib.faces))
    mesh.loops.foreach_set('vertex_index', unpack_list(ib.faces))
    # https://docs.blender.org/api/3.6/bpy.types.MeshPolygon.html#bpy.types.MeshPolygon.loop_start
    mesh.polygons.foreach_set('loop_start', [x * 3 for x in range(len(ib.faces))])
    mesh.polygons.foreach_set('loop_total', [3] * len(ib.faces))


def import_vertices(mesh, vb: VertexBuffer):
    mesh.vertices.add(len(vb.vertices))
    blend_indices = {}
    blend_weights = {}
    texcoords = {}
    vertex_layers = {}
    use_normals = False

    for elem in vb.layout:
        if elem.InputSlotClass != 'per-vertex':
            continue

        data = tuple(x[elem.name] for x in vb.vertices)
        if elem.name == 'POSITION':
            # Ensure positions are 3-dimensional:
            if len(data[0]) == 4:
                if ([x[3] for x in data] != [1.0] * len(data)):
                    # XXX: Leaving this fatal error in for now, as the meshes
                    # it triggers on in DOA6 (skirts) lie about almost every
                    # semantic and we cannot import them with this version of
                    # the script regardless. Comment it out if you want to try
                    # importing anyway and preserving the W coordinate in a
                    # vertex group. It might also be possible to project this
                    # back into 3D if we assume the coordinates are homogeneous
                    # (i.e. divide XYZ by W), but that might be assuming too
                    # much for a generic script.
                    raise Fatal('Positions are 4D')

                    # Nico: Blender暂时不支持4D索引，加了也没用，直接不行就报错，转人工处理。
                    # Occurs in some meshes in DOA6, such as skirts.
                    # W coordinate must be preserved in these cases.
                    # print('Positions are 4D, storing W coordinate in POSITION.w vertex layer')
                    # vertex_layers['POSITION.w'] = [[x[3]] for x in data]
            positions = [(x[0], x[1], x[2]) for x in data]
            mesh.vertices.foreach_set('co', unpack_list(positions))
        elif elem.name.startswith('COLOR'):
            if len(data[0]) <= 3 or vertex_color_layer_channels == 4:
                # Either a monochrome/RGB layer, or Blender 2.80 which uses 4
                # channel layers
                mesh.vertex_colors.new(name=elem.name)
                color_layer = mesh.vertex_colors[elem.name].data
                c = vertex_color_layer_channels
                for l in mesh.loops:
                    color_layer[l.index].color = list(data[l.vertex_index]) + [0] * (c - len(data[l.vertex_index]))
            else:
                mesh.vertex_colors.new(name=elem.name + '.RGB')
                mesh.vertex_colors.new(name=elem.name + '.A')
                color_layer = mesh.vertex_colors[elem.name + '.RGB'].data
                alpha_layer = mesh.vertex_colors[elem.name + '.A'].data
                for l in mesh.loops:
                    color_layer[l.index].color = data[l.vertex_index][:3]
                    alpha_layer[l.index].color = [data[l.vertex_index][3], 0, 0]
        elif elem.name == 'NORMAL':
            use_normals = True
            normals = [(x[0], x[1], x[2]) for x in data]
            mesh.create_normals_split()
            for l in mesh.loops:
                l.normal[:] = normals[l.vertex_index]
        elif elem.name in ('TANGENT', 'BINORMAL'):
            #    # XXX: loops.tangent is read only. Not positive how to handle
            #    # this, or if we should just calculate it when re-exporting.
            #    for l in mesh.loops:
            #        assert(data[l.vertex_index][3] in (1.0, -1.0))
            #        l.tangent[:] = data[l.vertex_index][0:3]
            print('NOTICE: Skipping import of %s in favour of recalculating on export' % elem.name)
        elif elem.name.startswith('BLENDINDICES'):
            blend_indices[elem.SemanticIndex] = data
        elif elem.name.startswith('BLENDWEIGHT'):
            blend_weights[elem.SemanticIndex] = data
        elif elem.name.startswith('TEXCOORD') and elem.is_float():
            texcoords[elem.SemanticIndex] = data
        else:
            print('NOTICE: Storing unhandled semantic %s %s as vertex layer' % (elem.name, elem.Format))
            vertex_layers[elem.name] = data

    return (blend_indices, blend_weights, texcoords, vertex_layers, use_normals)

def find_texture(texture_prefix, texture_suffix, directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(texture_suffix) and file.startswith(texture_prefix):
                texture_path = os.path.join(root, file)
                return texture_path
    return None

def create_material_with_texture(obj, mesh_name, directory):
    # Изменим имя текстуры, чтобы оно точно совпадало с шаблоном (Change the texture name to match the template exactly)
    material_name = f"{mesh_name}_Material"
    # texture_name = f"{mesh_name}-DiffuseMap.jpg"

    mesh_name_split = str(mesh_name).split(".")[0].split("-")
    texture_prefix = mesh_name_split[0] # IB Hash
    if len(mesh_name_split) > 1:
        texture_suffix = f"{mesh_name_split[1]}-DiffuseMap.tga" # Part Name
    else:
        texture_suffix = "-DiffuseMap.tga"

    # 查找是否存在满足条件的转换好的tga贴图文件

    texture_path = None

    # 查找是否存在满足条件的转换好的tga贴图文件
    texture_path = find_texture(texture_prefix, texture_suffix, directory)

    # 如果不存在，试试查找jpg文件
    if texture_path is None:
        if len(mesh_name_split) > 1:
            texture_suffix = f"{mesh_name_split[1]}-DiffuseMap.jpg"  # Part Name
        else:
            texture_suffix = "-DiffuseMap.jpg"
        # 查找jpg文件，如果这里没找到的话后面也是正常的，但是这里如果找到了就能起到兼容旧版本jpg文件的作用
        texture_path = find_texture(texture_prefix, texture_suffix, directory)

    # 如果还不存在，试试查找png文件
    if texture_path is None:
        if len(mesh_name_split) > 1:
            texture_suffix = f"{mesh_name_split[1]}-DiffuseMap.png"  # Part Name
        else:
            texture_suffix = "-DiffuseMap.png"
        # 查找jpg文件，如果这里没找到的话后面也是正常的，但是这里如果找到了就能起到兼容旧版本jpg文件的作用
        texture_path = find_texture(texture_prefix, texture_suffix, directory)


    # Nico: 这里如果没有检测到对应贴图则不创建材质，也不新建BSDF
    # 否则会造成合并模型后，UV编辑界面选择不同材质的UV会跳到不同UV贴图界面导致无法正常编辑的问题
    if texture_path is not None:
        # Создание нового материала (Create new materials)
        material = bpy.data.materials.new(name=material_name)
        material.use_nodes = True

        # Nico: Currently only support EN and ZH-CN
        bsdf = material.node_tree.nodes.get("原理化BSDF")
        if not bsdf:
            bsdf = material.node_tree.nodes.get("Principled BSDF")

        if bsdf:
            # Поиск текстуры (Search for textures)

            if texture_path:
                tex_image = material.node_tree.nodes.new('ShaderNodeTexImage')
                tex_image.image = bpy.data.images.load(texture_path)

                # 因为tga格式贴图有alpha通道，所以必须用CHANNEL_PACKED才能显示正常颜色
                tex_image.image.alpha_mode = "CHANNEL_PACKED"

                material.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])

            # Применение материала к мешу (Materials applied to bags)
            if obj.data.materials:
                obj.data.materials[0] = material
            else:
                obj.data.materials.append(material)




def read_vertexbuffer_indexbuffer(operator, paths):
    vb_paths, ib_paths, use_bin = zip(*paths)
    if len(vb_paths) != 1 or len(ib_paths) > 1:
        raise Fatal('暂不支持从加载的bin文件中融合多个文件')

    vb_bin_path, vb_txt_path = vb_paths[0]
    ib_bin_path, ib_txt_path = ib_paths[0]

    vb = VertexBuffer(open(vb_txt_path, 'r'), load_vertices=False)
    vb.parse_vb_bin(open(vb_bin_path, 'rb'))

    ib = IndexBuffer(open(ib_txt_path, 'r'), load_indices=False)
    ib.parse_ib_bin(open(ib_bin_path, 'rb'))

    return vb, ib, os.path.basename(vb_bin_path)


# TODO 为什么要flip_texcoord_v?
def import_3dmigoto_vb_ib_to_obj(operator, context, paths, flip_texcoord_v=True, axis_forward='-Z', axis_up='Y'):

    # 获取vb和ib抽象出的数据，顺便获取最终导入后的名称为 .vb结尾
    vb, ib, name = read_vertexbuffer_indexbuffer(operator, paths)

    # 创建mesh和Object对象，用于后续填充
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(mesh.name, mesh)

    # 设置坐标系
    global_matrix = axis_conversion(from_forward=axis_forward, from_up=axis_up).to_4x4()
    obj.matrix_world = global_matrix

    # Attach the vertex buffer layout to the object for later exporting. Can't
    # seem to retrieve this if attached to the mesh - to_mesh() doesn't copy it:
    obj['3DMigoto:VBLayout'] = vb.layout.serialise()
    obj['3DMigoto:VBStride'] = vb.layout.stride
    obj['3DMigoto:FirstVertex'] = vb.first
    obj['3DMigoto:IBFormat'] = ib.format
    obj['3DMigoto:FirstIndex'] = ib.first

    import_faces_from_ib(mesh, ib)

    (blend_indices, blend_weights, texcoords, vertex_layers, use_normals) = import_vertices(mesh, vb)

    import_uv_layers(mesh, obj, texcoords, flip_texcoord_v)

    import_vertex_groups(mesh, obj, blend_indices, blend_weights)

    # Validate closes the loops so they don't disappear after edit mode and probably other important things:
    mesh.validate(verbose=False, clean_customdata=False)  # *Very* important to not remove lnors here!
    # 这里的lnors可能指的是mesh.loop里的normal？
    # Not actually sure update is necessary. It seems to update the vertex normals, not sure what else:
    mesh.update()

    # Must be done after validate step:
    if use_normals:
        # Taken from import_obj/import_fbx
        clnors = array('f', [0.0] * (len(mesh.loops) * 3))
        mesh.loops.foreach_get("normal", clnors)
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.normals_split_custom_set(tuple(zip(*(iter(clnors),) * 3)))
    else:
        mesh.calc_normals()

    link_object_to_scene(context, obj)
    obj.select_set(True)
    set_active_object(context, obj)

    operator.report({'INFO'}, "导入成功!")

    # TODO 这里用到bmesh的部分删了也没事，到底有什么用呢？
    import bmesh
    # 创建 BMesh 副本
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # 将 BMesh 更新回原始网格
    bm.to_mesh(mesh)
    bm.free()

    # 设置导入时的顶点数和索引数，用于插件右键对比是否和原本顶点数量一致
    obj['3DMigoto:OriginalVertexNumber'] = len(mesh.vertices)
    obj['3DMigoto:OriginalIndicesNumber'] = len(mesh.loops)

    # 自动贴图导入
    mesh_prefix: str = str(mesh.name).split(".")[0]
    # operator.report({'INFO'}, mesh_prefix)
    create_material_with_texture(obj, mesh_prefix, os.path.dirname(paths[0][0][0]))
    return obj


def import_3dmigoto_raw_buffers(operator, context, vb_fmt_path, ib_fmt_path, vb_path=None, ib_path=None, **kwargs):
    # 这里的True好像是use_bin?
    paths = (((vb_path, vb_fmt_path), (ib_path, ib_fmt_path), True),)
    obj = []
    for p in paths:
        try:
            obj.append(import_3dmigoto_vb_ib_to_obj(operator, context, [p], **kwargs))
        except Fatal as e:
            operator.report({'ERROR'}, str(e) + ': ' + str(p[:2]))
    # FIXME: Group objects together  (Nico:这里他的意思应该是导入后自动放入一个集合里，我们也需要这个功能)
    return obj


class Import3DMigotoRaw(bpy.types.Operator, ImportHelper):
    """Import raw 3DMigoto vertex and index buffers"""
    bl_idname = "import_mesh.migoto_raw_buffers_mmt"
    bl_label = "导入3Dmigoto的原始Buffer文件"
    bl_options = {'UNDO'}

    filename_ext = '.vb;.ib;.fmt'
    filter_glob: StringProperty(
        default='*.vb;*.ib;*.fmt',
        options={'HIDDEN'},
    ) # type: ignore

    files: CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    ) # type: ignore

    # 这里flip_texcoord_v是因为我们游戏里Dump出来的图片是逆向的，所以这里要flip一下才能对上
    # 理论上可以去掉，设为总是flip对吗？
    flip_texcoord_v: BoolProperty(
        name="Flip TEXCOORD V",
        description="Flip TEXCOORD V asix during importing",
        default=True,
    ) # type: ignore

    # 判断相关文件是否存在
    def get_vb_ib_paths(self, filename):
        vb_bin_path = os.path.splitext(filename)[0] + '.vb'
        ib_bin_path = os.path.splitext(filename)[0] + '.ib'
        fmt_path = os.path.splitext(filename)[0] + '.fmt'
        if not os.path.exists(vb_bin_path):
            raise Fatal('Unable to find matching .vb file for %s' % filename)
        if not os.path.exists(ib_bin_path):
            raise Fatal('Unable to find matching .ib file for %s' % filename)
        if not os.path.exists(fmt_path):
            fmt_path = None
        return (vb_bin_path, ib_bin_path, fmt_path)

    def execute(self, context):
        migoto_raw_import_options = self.as_keywords(ignore=('filepath', 'files', 'filter_glob'))

        # 我们需要添加到一个新建的集合里，方便后续操作
        # 这里集合的名称需要为当前文件夹的名称
        collection_name = os.path.basename(os.path.dirname(self.filepath))
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

        done = set()
        dirname = os.path.dirname(self.filepath)
        for filename in self.files:
            try:
                (vb_path, ib_path, fmt_path) = self.get_vb_ib_paths(os.path.join(dirname, filename.name))
                if os.path.normcase(vb_path) in done:
                    continue
                done.add(os.path.normcase(vb_path))

                if fmt_path is not None:
                    # 导入的调用链就从这里开始
                    obj_results = import_3dmigoto_raw_buffers(self, context, fmt_path, fmt_path, vb_path=vb_path, ib_path=ib_path, **migoto_raw_import_options)
                    for obj in obj_results:
                        # 因为之前导入的过程中链接到scene了，所以必选在这里先断开链接否则会出现两个实例
                        bpy.context.scene.collection.objects.unlink(obj)
                        # 再链接到集合，就能显示在集合下面了
                        collection.objects.link(obj)
                        
                else:
                    self.report({'ERROR'}, "未找到.fmt文件，无法导入")
            except Fatal as e:
                self.report({'ERROR'}, str(e))
        return {'FINISHED'}
    

class MMTImportAllVbModel(bpy.types.Operator):
    bl_idname = "mmt.import_all"
    bl_label = "Import all .ib .vb model from current OutputFolder"
    bl_options = {'UNDO'}

    def execute(self, context):
        # 首先根据MMT路径，获取
        mmt_path = bpy.context.scene.mmt_props.path
        current_game = ""
        main_setting_path = os.path.join(context.scene.mmt_props.path, "Configs\\Main.json")
        if os.path.exists(main_setting_path):
            main_setting_file = open(main_setting_path)
            main_setting_json = json.load(main_setting_file)
            main_setting_file.close()
            current_game = main_setting_json["GameName"]

        game_config_path = os.path.join(context.scene.mmt_props.path, "Games\\" + current_game + "\\Config.json")
        game_config_file = open(game_config_path)
        game_config_json = json.load(game_config_file)
        game_config_file.close()

        output_folder_path = mmt_path + "Games\\" + current_game + "\\3Dmigoto\\Mods\\output\\"

        # 这里是根据Config.json中的DrawIB来决定导入时导入具体哪个IB
        import_folder_path_list = []
        for ib_config in game_config_json:
            draw_ib = ib_config["DrawIB"]
            # print("DrawIB:", draw_ib)
            import_folder_path_list.append(os.path.join(output_folder_path, draw_ib))

        # self.report({'INFO'}, "读取到的drawIB文件夹总数量：" + str(len(import_folder_path_list)))

        for import_folder_path in import_folder_path_list:
            # TODO 在这里导入当前文件夹下所有的ib vb文件
            # 1.我们需要添加到一个新建的集合里，方便后续操作
            folder_draw_ib_name = os.path.basename(import_folder_path)
            collection = bpy.data.collections.new(folder_draw_ib_name)
            bpy.context.scene.collection.children.link(collection)

            # 每个import_folder_path都是一个drawIB
            # 这里我们需要获取到文件夹名称
            # 获取文件夹名称

            # 读取文件夹下面所有的vb和ib文件的prefix
            prefix_set = set()
            # (1) 获取所有ib文件前缀列表
            # self.report({'INFO'}, "Folder Name：" + import_folder_path)
            # 构造需要匹配的文件路径模式
            file_pattern = os.path.join(import_folder_path, "*.ib")
            # 使用 glob.glob 获取匹配的文件列表
            txt_file_list = glob(file_pattern)
            for txt_file_path in txt_file_list:
                # 如果文件名不包含-则属于我们自动导出的文件名，则不计入统计
                if os.path.basename(txt_file_path).find("-") == -1:
                    continue

                # self.report({'INFO'}, "txt file: " + txt_file_path)
                txt_file_splits = os.path.basename(txt_file_path).split("-")
                ib_file_name = txt_file_splits[0] + "-" + txt_file_splits[1]
                ib_file_name = ib_file_name[0:len(ib_file_name) - 3]
                prefix_set.add(ib_file_name)
            # 遍历并导入每一个ib vb文件
            for prefix in prefix_set:
                vb_bin_path = import_folder_path + "\\" + prefix + '.vb'
                ib_bin_path = import_folder_path + "\\" + prefix + '.ib'
                fmt_path = import_folder_path + "\\" + prefix + '.fmt'
                if not os.path.exists(vb_bin_path):
                    raise Fatal('Unable to find matching .vb file for %s' % import_folder_path + "\\" + prefix)
                if not os.path.exists(ib_bin_path):
                    raise Fatal('Unable to find matching .ib file for %s' % import_folder_path + "\\" + prefix)
                if not os.path.exists(fmt_path):
                    fmt_path = None

                # 一些需要传递过去的参数，反正这里传空的是可以用的
                migoto_raw_import_options = {}

                # 这里使用一个done的set来记录已经处理过的文件路径，如果处理过就会在里面触发continue
                done = set()
                try:
                    if os.path.normcase(vb_bin_path) in done:
                        continue
                    done.add(os.path.normcase(vb_bin_path))
                    if fmt_path is not None:
                        obj_results = import_3dmigoto_raw_buffers(self, context, fmt_path, fmt_path, vb_path=vb_bin_path,
                                                                  ib_path=ib_bin_path, **migoto_raw_import_options)
                        for obj in obj_results:
                             # 因为之前导入的过程中链接到scene了，所以必选在这里先断开链接否则会出现两个实例
                            bpy.context.scene.collection.objects.unlink(obj)
                            # 再链接到集合，就能显示在集合下面了
                            collection.objects.link(obj)
                    else:
                        self.report({'ERROR'}, "Can't find .fmt file!")
                except Fatal as e:
                    self.report({'ERROR'}, str(e))

        return {'FINISHED'}
