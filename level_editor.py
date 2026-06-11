import math
import sys
import os

# bpy (Blender Python API) および mathutils はBlender内でのみ動作するため、
# 通常のPython環境で直接実行された場合はメッセージを出して安全に終了させます。
try:
    import bpy
    import bpy_extras
    from mathutils import Vector
except ImportError:
    print("-" * 60)
    print("【お知らせ】")
    print("このスクリプトは3Dソフト「Blender」のアドオンプログラムです。")
    print("VS Codeや通常のPythonターミナルから直接実行することはできません。")
    print("\n[確認方法]")
    print("1. Blenderを起動します。")
    print("2. プリファレンスのアドオン設定からこのスクリプトを登録・有効化してください。")
    print("3. Blender内の「MyMenu」メニューから機能を実行できます。")
    print("-" * 60)
    sys.exit(0)

# ブレンダーに登録するアドオン情報
bl_info = {
    "name": "レベルエディタ",
    "author": "Taro Kamata",
    "version": (1, 0),
    "blender": (3, 3, 1),
    "location": "",
    "description": "レベルエディタ",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}

#オペレータ 頂点を伸ばす
class MYADDON_OT_stretch_vertex(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_stretch_vertex"
    bl_label = "頂点を伸ばす"
    bl_description = "頂点座標を引っ張って伸ばします"
    #リドゥ、アンドゥ可能オプション
    bl_options = {'REGISTER', 'UNDO'}

    #メニューを実行したときに呼ばれるコールバック関数
    def execute(self, context):
        bpy.data.objects["Cube"].data.vertices[0].co.x += 1.0
        print("頂点を伸ばしました。 ")

        #オペレータの命令終了を通知
        return {'FINISHED'}

#オペレータ ICO球生成
class MYADDON_OT_create_ico_sphere(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_create_object"
    bl_label = "ICO球生成"
    bl_description = "ICO球を生成します"
    bl_options = {'REGISTER', 'UNDO'}

    # メニューを実行したときに呼ばれる関数
    def execute(self, context):
        bpy.ops.mesh.primitive_ico_sphere_add()
        print("ICO球を生成しました。 ")

        return {'FINISHED'}

# プレイヤーパラメータを共有ファイルからロード
def load_player_parameters():
    path = "C:/Users/k024g/Desktop/GE3&CG3/project/Resources/player_params.txt"
    params = {
        "LIMIT_X": 35.0,
        "LIMIT_Y": 25.0,
        "COLLISION_RADIUS": 2.0
    }
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    try:
                        params[key] = float(val)
                    except ValueError:
                        pass
    return params

# 警告用赤マテリアルの取得または新規作成
def get_or_create_warning_material():
    mat = bpy.data.materials.get("Warning_Red")
    if not mat:
        mat = bpy.data.materials.new("Warning_Red")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        principled = nodes.get("Principled BSDF")
        if principled:
            principled.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)
            if 'Emission Color' in principled.inputs:
                principled.inputs['Emission Color'].default_value = (1.0, 0.0, 0.0, 1.0)
            elif 'Emission' in principled.inputs:
                principled.inputs['Emission'].default_value = (1.0, 0.0, 0.0, 1.0)
    return mat

# オペレータ セーフティトンネル生成
class MYADDON_OT_generate_tunnel(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_generate_tunnel"
    bl_label = "セーフティトンネル生成"
    bl_description = "PlayerRailカーブに沿って自機移動可能領域のトンネルを生成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        params = load_player_parameters()
        limit_x = params["LIMIT_X"]
        limit_y = params["LIMIT_Y"]
        radius = params["COLLISION_RADIUS"]
        
        w = limit_x + radius
        h = limit_y + radius
        
        curve_obj = bpy.data.objects.get("PlayerRail")
        if not curve_obj or curve_obj.type != 'CURVE':
            self.report({'WARNING'}, "シーンに 'PlayerRail' という名前のカーブオブジェクトが見つかりません。")
            return {'CANCELLED'}
            
        old_tunnel = bpy.data.objects.get("SafetyTunnel")
        if old_tunnel:
            bpy.data.objects.remove(old_tunnel, do_unlink=True)
            
        active_obj = context.active_object
        
        # カーブを複製してメッシュに変換
        bpy.ops.object.select_all(action='DESELECT')
        curve_obj.select_set(True)
        context.view_layer.objects.active = curve_obj
        bpy.ops.object.duplicate()
        temp_curve_obj = context.active_object
        
        bpy.ops.object.convert(target='MESH')
        temp_mesh_obj = context.active_object
        
        vertices = [v.co.copy() for v in temp_mesh_obj.data.vertices]
        
        bpy.data.objects.remove(temp_mesh_obj, do_unlink=True)
        
        if active_obj:
            context.view_layer.objects.active = active_obj
            
        if len(vertices) < 2:
            self.report({'WARNING'}, "PlayerRail の頂点数が足りません。")
            return {'CANCELLED'}
            
        points = vertices
        num_points = len(points)
        
        mesh_data = bpy.data.meshes.new("SafetyTunnelMesh")
        tunnel_obj = bpy.data.objects.new("SafetyTunnel", mesh_data)
        context.collection.objects.link(tunnel_obj)
        
        import bmesh
        bm = bmesh.new()
        
        section_verts = []
        for i in range(num_points):
            p = points[i]
            
            if i < num_points - 1:
                tangent = (points[i+1] - p).normalized()
            else:
                tangent = (p - points[i-1]).normalized()
                
            up_ref = Vector((0.0, 1.0, 0.0))
            if abs(tangent.dot(up_ref)) > 0.999:
                up_ref = Vector((1.0, 0.0, 0.0))
                
            right = tangent.cross(up_ref).normalized()
            up = right.cross(tangent).normalized()
            
            v0 = p - right * w - up * h
            v1 = p + right * w - up * h
            v2 = p + right * w + up * h
            v3 = p - right * w + up * h
            
            bm_v0 = bm.verts.new(v0)
            bm_v1 = bm.verts.new(v1)
            bm_v2 = bm.verts.new(v2)
            bm_v3 = bm.verts.new(v3)
            section_verts.append((bm_v0, bm_v1, bm_v2, bm_v3))
            
        for i in range(num_points - 1):
            s1 = section_verts[i]
            s2 = section_verts[i+1]
            
            bm.faces.new((s1[0], s1[1], s2[1], s2[0]))
            bm.faces.new((s1[1], s1[2], s2[2], s2[1]))
            bm.faces.new((s1[2], s1[3], s2[3], s2[2]))
            bm.faces.new((s1[3], s1[0], s2[0], s2[3]))
            
        bm.faces.new((section_verts[0][3], section_verts[0][2], section_verts[0][1], section_verts[0][0]))
        bm.faces.new((section_verts[-1][0], section_verts[-1][1], section_verts[-1][2], section_verts[-1][3]))
        
        bm.to_mesh(mesh_data)
        bm.free()
        
        mat = bpy.data.materials.get("SafetyTunnelMaterial")
        if not mat:
            mat = bpy.data.materials.new("SafetyTunnelMaterial")
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            principled = nodes.get("Principled BSDF")
            if principled:
                principled.inputs['Base Color'].default_value = (1.0, 0.8, 0.0, 1.0)
                principled.inputs['Alpha'].default_value = 0.2
            mat.blend_method = 'BLEND'
            
        if len(tunnel_obj.data.materials) == 0:
            tunnel_obj.data.materials.append(mat)
        else:
            tunnel_obj.data.materials[0] = mat
            
        tunnel_obj.show_wire = True
        tunnel_obj.display_type = 'TEXTURED'
        
        self.report({'INFO'}, f"セーフティトンネルを生成しました。X可動幅={limit_x:.1f}, Y可動幅={limit_y:.1f}, 判定半径={radius:.1f}")
        return {'FINISHED'}

# オペレータ 衝突干渉判定
class MYADDON_OT_check_collision(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_check_collision"
    bl_label = "衝突干渉判定"
    bl_description = "セーフティトンネルと障害物メッシュの交差（干渉）を検知し、赤く警告します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        tunnel_obj = bpy.data.objects.get("SafetyTunnel")
        if not tunnel_obj or tunnel_obj.type != 'MESH':
            self.report({'WARNING'}, "セーフティトンネルがありません。先に「セーフティトンネル生成」を実行してください。")
            return {'CANCELLED'}
            
        depsgraph = context.evaluated_depsgraph_get()
        
        try:
            from mathutils.bvhtree import BVHTree
            tunnel_tree = BVHTree.FromObject(tunnel_obj, depsgraph)
        except Exception as e:
            self.report({'WARNING'}, f"セーフティトンネルの衝突モデル作成に失敗しました: {e}")
            return {'CANCELLED'}
            
        warning_mat = get_or_create_warning_material()
        collision_count = 0
        
        for obj in bpy.context.scene.objects:
            if obj == tunnel_obj or obj.type != 'MESH' or obj.name == "PlayerRail":
                continue
                
            try:
                obj_tree = BVHTree.FromObject(obj, depsgraph)
            except Exception:
                continue
                
            overlap = tunnel_tree.overlap(obj_tree)
            
            if overlap:
                collision_count += 1
                if len(obj.data.materials) > 0:
                    current_mat = obj.data.materials[0]
                    if current_mat != warning_mat:
                        obj["original_material_name"] = current_mat.name
                    obj.data.materials[0] = warning_mat
                else:
                    obj.data.materials.append(warning_mat)
                    obj["original_material_name"] = ""
            else:
                if "original_material_name" in obj:
                    orig_name = obj["original_material_name"]
                    if orig_name:
                        orig_mat = bpy.data.materials.get(orig_name)
                        if orig_mat and len(obj.data.materials) > 0:
                            obj.data.materials[0] = orig_mat
                    else:
                        if len(obj.data.materials) > 0:
                            obj.data.materials.clear()
                    del obj["original_material_name"]
                    
        self.report({'INFO'}, f"衝突干渉判定を完了しました。干渉オブジェクト数: {collision_count}")
        return {'FINISHED'}

# オペレータ 警告クリア
class MYADDON_OT_clear_warning(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_clear_warning"
    bl_label = "警告クリア"
    bl_description = "障害物メッシュの警告色（赤マテリアル）を元の状態に戻します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        warning_mat = bpy.data.materials.get("Warning_Red")
        restored_count = 0
        
        for obj in bpy.context.scene.objects:
            if obj.type != 'MESH':
                continue
                
            if "original_material_name" in obj:
                orig_name = obj["original_material_name"]
                if orig_name:
                    orig_mat = bpy.data.materials.get(orig_name)
                    if orig_mat and len(obj.data.materials) > 0:
                        obj.data.materials[0] = orig_mat
                        restored_count += 1
                else:
                    if len(obj.data.materials) > 0:
                        obj.data.materials.clear()
                        restored_count += 1
                del obj["original_material_name"]
            elif len(obj.data.materials) > 0 and obj.data.materials[0] == warning_mat:
                obj.data.materials.clear()
                restored_count += 1
                
        self.report({'INFO'}, f"警告色をクリアしました。復元オブジェクト数: {restored_count}")
        return {'FINISHED'}

# C++シーンレイアウトインポート用のマテリアル取得・作成関数
def get_or_create_import_material(name, color):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        principled = nodes.get("Principled BSDF")
        if principled:
            principled.inputs['Base Color'].default_value = color
    return mat

# プレイヤーモデルのインポート処理
def import_player_model(location):
    # すでにプレイヤーオブジェクトが存在する場合は削除してからインポート
    old_player = bpy.data.objects.get("Game_Player")
    if old_player:
        bpy.data.objects.remove(old_player, do_unlink=True)
        
    obj_path = "C:/Users/k024g/Desktop/GE3&CG3/project/Resources/Player2/Player.obj"
    if not os.path.exists(obj_path):
        return None
    
    # 選択解除
    bpy.ops.object.select_all(action='DESELECT')
    
    # インポート
    try:
        bpy.ops.wm.obj_import(filepath=obj_path)
    except AttributeError:
        bpy.ops.import_scene.obj(filepath=obj_path)
        
    # インポートされたオブジェクトの取得
    imported_objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not imported_objs:
        return None
        
    # 複数オブジェクトをバインドするための親オブジェクトを生成
    player_root = bpy.data.objects.new("Game_Player", None)
    bpy.context.scene.collection.objects.link(player_root)
    
    # ワールド座標を崩さず結ぶため、一度原点で親子関係を作成
    player_root.location = (0.0, 0.0, 0.0)
    player_root.scale = (1.0, 1.0, 1.0)
    
    for child in imported_objs:
        child.parent = player_root
        child.name = "Game_Player_Mesh"
        
    # 親子関係が結ばれた後に、親を目標の位置・スケールに設定
    player_root.location = location
    player_root.scale = (5.0, 5.0, 5.0)
    player_root.rotation_euler = (0.0, 0.0, 0.0)
    
    # 選択解除
    bpy.ops.object.select_all(action='DESELECT')
    return player_root

# 敵モデルのインポート処理
def import_enemy_model(location, scale_val=(1.0, 1.0, 1.0), rotation_val=(0.0, 0.0, 0.0)):
    obj_path = "C:/Users/k024g/Desktop/GE3&CG3/project/Resources/Player/player.obj"
    if not os.path.exists(obj_path):
        return None
    
    # 選択解除
    bpy.ops.object.select_all(action='DESELECT')
    
    # インポート
    try:
        bpy.ops.wm.obj_import(filepath=obj_path)
    except AttributeError:
        bpy.ops.import_scene.obj(filepath=obj_path)
        
    # インポートされたオブジェクトの取得
    imported_objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    if not imported_objs:
        return None
        
    # 複数オブジェクトをバインドするための親オブジェクトを生成
    enemy_root = bpy.data.objects.new("Game_Enemy", None)
    bpy.context.scene.collection.objects.link(enemy_root)
    
    # ワールド座標を崩さず結ぶため、一度原点で親子関係を作成
    enemy_root.location = (0.0, 0.0, 0.0)
    enemy_root.scale = (1.0, 1.0, 1.0)
    
    for child in imported_objs:
        child.parent = enemy_root
        child.name = "Game_Enemy_Mesh"
        
    # 親子関係が結ばれた後に、親を目標の位置・スケール・回転に設定
    enemy_root.location = location
    # 敵の等倍表示のため、C++スケール(scale_val)にBlenderサイズ比0.5を掛けて 5.0 倍
    enemy_root.scale = (scale_val[0] * 5.0, scale_val[2] * 5.0, scale_val[1] * 5.0)
    enemy_root.rotation_euler = (math.radians(rotation_val[0]), math.radians(rotation_val[2]), math.radians(rotation_val[1]))
    
    # 選択解除
    bpy.ops.object.select_all(action='DESELECT')
    return enemy_root

# オペレータ C++シーンレイアウト読込
class MYADDON_OT_import_layout(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_import_layout"
    bl_label = "C++シーンレイアウト読込"
    bl_description = "C++ゲームエンジンが出力したscene_layout.txtから障害物と床を読み込み、配置します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        path = "C:/Users/k024g/Desktop/GE3&CG3/project/Resources/scene_layout.txt"
        if not os.path.exists(path):
            self.report({'WARNING'}, f"シーンレイアウトファイルが見つかりません: {path}\nゲームを一度起動してファイルを生成してください。")
            return {'CANCELLED'}

        # 既存の Game_ で始まるオブジェクトを削除
        for obj in list(bpy.context.scene.objects):
            if obj.name.startswith("Game_"):
                bpy.data.objects.remove(obj, do_unlink=True)

        # マテリアルを用意
        building_mat = get_or_create_import_material("Game_Building_Mat", (0.5, 0.6, 0.7, 1.0))
        floor_mat = get_or_create_import_material("Game_Floor_Mat", (0.2, 0.2, 0.25, 1.0))

        imported_count = 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    tokens = line.split(',')
                    if len(tokens) < 7:
                        continue
                    
                    type_name = tokens[0].strip()
                    try:
                        x = float(tokens[1])
                        y = float(tokens[2])
                        z = float(tokens[3])
                        sx = float(tokens[4])
                        sy = float(tokens[5])
                        sz = float(tokens[6])
                    except ValueError:
                        continue

                    rx, ry, rz = 0.0, 0.0, 0.0
                    if len(tokens) >= 10:
                        try:
                            rx = float(tokens[7])
                            ry = float(tokens[8])
                            rz = float(tokens[9])
                        except ValueError:
                            pass

                    # 座標変換: C++ (x, y, z) -> Blender (x, z, y)
                    loc = (x, z, y)
                    # スケール変換: C++ (sx, sy, sz) -> Blender (sx * 0.5, sz * 0.5, sy * 0.5)
                    scale = (sx * 0.5, sz * 0.5, sy * 0.5)
                    # 回転変換
                    rot = (math.radians(rx), math.radians(rz), math.radians(ry))

                    # 作成前の選択状態をクリア
                    bpy.ops.object.select_all(action='DESELECT')

                    if type_name == "BUILDING":
                        bpy.ops.mesh.primitive_cube_add(size=2.0)
                        obj = context.active_object
                        obj.name = "Game_Building"
                        obj.location = loc
                        obj.scale = scale
                        obj.rotation_euler = rot
                        obj.data.materials.append(building_mat)
                        imported_count += 1

                    elif type_name == "FLOOR":
                        bpy.ops.mesh.primitive_plane_add(size=2.0)
                        obj = context.active_object
                        obj.name = "Game_Floor"
                        obj.location = loc
                        obj.scale = scale
                        obj.rotation_euler = rot
                        obj.data.materials.append(floor_mat)
                        imported_count += 1
                        
                    elif type_name == "PLAYER":
                        import_player_model(loc)
                        imported_count += 1
                        
                    elif type_name == "ENEMY":
                        import_enemy_model(loc, scale, (rx, ry, rz))
                        imported_count += 1
                        
            # 作成後の選択状態をクリア
            bpy.ops.object.select_all(action='DESELECT')
            
        except Exception as e:
            self.report({'ERROR'}, f"ファイルの読み込みに失敗しました: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"シーンレイアウトを読み込みました。配置数: {imported_count}")
        return {'FINISHED'}

# リアルタイム同期用のグローバル状態と関数群
sync_timer_active = False

def sync_timer_callback():
    global sync_timer_active
    if not sync_timer_active:
        return None # タイマーを停止
        
    path = "C:/Users/k024g/Desktop/GE3&CG3/project/Resources/player_actual_pos.txt"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    tokens = content.split(',')
                    if len(tokens) >= 3:
                        x = float(tokens[0])
                        y = float(tokens[1])
                        z = float(tokens[2])
                        
                        # C++ (x, y, z) -> Blender (x, z, y)
                        loc = (x, z, y)
                        
                        # Game_Player オブジェクトを検索
                        player_obj = bpy.data.objects.get("Game_Player")
                        if player_obj:
                            player_obj.location = loc
                        else:
                            # 存在しなければ新規インポート
                            import_player_model(loc)
        except Exception:
            pass
            
    return 0.03 # 30ms後に再読み込み

class MYADDON_OT_realtime_sync(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_realtime_sync"
    bl_label = "C++実行位置とリアルタイム同期"
    bl_description = "C++ゲームのプレイ中に、自機の位置をBlender上にリアルタイム同期します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global sync_timer_active
        
        if sync_timer_active:
            sync_timer_active = False
            self.report({'INFO'}, "リアルタイム同期を停止しました。")
        else:
            sync_timer_active = True
            bpy.app.timers.register(sync_timer_callback)
            self.report({'INFO'}, "リアルタイム同期を開始しました。C++ゲームを起動して操作してください。")
            
        return {'FINISHED'}

#オペレータ シーン出力
class MYADDON_OT_export_scene(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"
    bl_options = {'REGISTER', 'UNDO'}

    # 出力するファイルの拡張子
    filename_ext = ".scene"

    def write_and_print(self, file, str):
        print(str)
        file.write(str)
        file.write('\n')

    def parse_scene_recursive(self, file, object, level):
        """シーン解析用再帰関数"""

        # 深さ分インデントする（タブを挿入）
        indent = ''
        for i in range(level):
            indent += "\t"

        # オブジェクト名書き込み
        self.write_and_print(file, indent + object.type + " - " + object.name)
        trans, rot, scale = object.matrix_local.decompose()
        # 回転を Quaternion から Euler (3軸での回転角) に変換
        rot = rot.to_euler()
        # ラジアンから度数法に変換
        rot.x = math.degrees(rot.x)
        rot.y = math.degrees(rot.y)
        rot.z = math.degrees(rot.z)

        # トランスフォーム情報を表示
        self.write_and_print(file, indent + "Trans(%f,%f,%f)" % (trans.x, trans.y, trans.z))
        self.write_and_print(file, indent + "Rot(%f,%f,%f)" % (rot.x, rot.y, rot.z))
        self.write_and_print(file, indent + "Scale(%f,%f,%f)" % (scale.x, scale.y, scale.z))
        self.write_and_print(file, '')

        # 子ノードへ進む（深さが1上がる）
        for child in object.children:
            self.parse_scene_recursive(file, child, level + 1)

    def export(self):
        """ファイルに出力"""
        print("シーン情報出力開始... %r" % self.filepath)
        # ファイルをテキスト形式で書き出し用にオープン
        # スコープを抜けると自動的にクローズされる
        with open(self.filepath, "wt") as file:
            # ファイルに文字列を書き込む
            self.write_and_print(file, "SCENE")

            # シーン内の全オブジェクトについて
            for object in bpy.context.scene.objects:
                # 親オブジェクトがあるものはスキップ（代わりに親から呼び出すから）
                if (object.parent):
                    continue

                # シーン直下のオブジェクトをルートノード(深さ0)とし、再帰関数で走査
                self.parse_scene_recursive(file, object, 0)

    #メニューを実行したときに呼ばれるコールバック関数
    def execute(self, context):
        print("シーン情報をExportします")

        # ファイルに出力
        self.export()

        print("シーン情報をExportしました")
        self.report({'INFO'}, "シーン情報をExportしました")

        #オペレータの命令終了を通知
        return {'FINISHED'}

#トップバーの拡張メニュー
class TOPBAR_MT_my_menu(bpy.types.Menu):
    #Blenderがクラスを識別する為の固有の文字列
    bl_idname = "myaddon.topbar_mt_my_menu"
    #メニューのラベルとして表示される文字列
    bl_label = "MyMenu"
    #著者表示用の文字列
    bl_description = "拡張メニュー by " + bl_info["author"]

    # サブメニューの描画
    def draw(self, context):

        #トップバーの「エディターメニュー」に項目（オペレータ）を追加
        self.layout.operator(MYADDON_OT_stretch_vertex.bl_idname,
            text=MYADDON_OT_stretch_vertex.bl_label)
        self.layout.operator(MYADDON_OT_create_ico_sphere.bl_idname,
            text=MYADDON_OT_create_ico_sphere.bl_label)
        self.layout.operator(MYADDON_OT_export_scene.bl_idname,
            text=MYADDON_OT_export_scene.bl_label)
        self.layout.separator()
        self.layout.operator(MYADDON_OT_import_layout.bl_idname,
            text=MYADDON_OT_import_layout.bl_label)
        self.layout.operator(MYADDON_OT_realtime_sync.bl_idname,
            text=MYADDON_OT_realtime_sync.bl_label)
        self.layout.separator()
        self.layout.operator(MYADDON_OT_generate_tunnel.bl_idname,
            text=MYADDON_OT_generate_tunnel.bl_label)
        self.layout.operator(MYADDON_OT_check_collision.bl_idname,
            text=MYADDON_OT_check_collision.bl_label)
        self.layout.operator(MYADDON_OT_clear_warning.bl_idname,
            text=MYADDON_OT_clear_warning.bl_label)

    # 既存のメニューにサブメニューを追加
    def submenu(self, context):

        # ID指定でサブメニューを追加
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)

# Blenderに登録するクラスリスト
classes = (
    MYADDON_OT_stretch_vertex,
    MYADDON_OT_create_ico_sphere,
    MYADDON_OT_export_scene,
    MYADDON_OT_import_layout,
    MYADDON_OT_realtime_sync,
    MYADDON_OT_generate_tunnel,
    MYADDON_OT_check_collision,
    MYADDON_OT_clear_warning,
    TOPBAR_MT_my_menu,
)

#Add-On有効化時コールバック
def register():
    # Blenderにクラスを登録
    for cls in classes:
        bpy.utils.register_class(cls)

    #メニューに項目を追加
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_my_menu.submenu)
    print("レベルエディタが有効化されました。 ")

#Add-On無効化時コールバック
def unregister():
    #メニューから項目を削除
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_my_menu.submenu)

    # Blenderからクラスを削除
    for cls in classes:
        bpy.utils.unregister_class(cls)
    print("レベルエディタが無効化されました。 ")

# テスト実行用コード
if __name__ == "__main__":
    register()
