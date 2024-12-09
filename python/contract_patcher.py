global loc_dic, loc_dic_en


def cfg_to_dict(cfg_text):
    # 字符串去注释
    lines = cfg_text.splitlines()
    lines = [line.strip() for line in lines]
    lines = [line.split("//")[0] for line in lines]
    lines = [line.strip() for line in lines]

    depth = 0
    ret = {}
    curs = [ret]  # 节点栈

    for i in range(len(lines) - 1):
        line = lines[i]
        next_line = lines[i + 1]
        if "{" in next_line:
            # 左括号 加层数
            depth += 1
            if line not in curs[-1]:
                curs[-1][line] = []
            curs[-1][line].append({})
            curs.append(curs[-1][line][-1])
            continue
        if "=" in line:
            # 有等号 键值对
            key, value = line.split("=", 1)
            curs[-1][key.strip()] = value.strip()
        if "}" in next_line:
            # 右括号 减层数
            depth -= 1
            curs.pop()
    return ret


def dict_to_cfg(d, indent=0):
    cfg_text = ""
    indent_str = "    " * indent

    for key, value in d.items():
        if isinstance(value, list):  # 处理列表情况
            for item in value:
                cfg_text += f"{indent_str}{key}\n{indent_str}{{\n"
                cfg_text += dict_to_cfg(item, indent + 1)  # 递归处理列表中的字典
                cfg_text += f"{indent_str}}}\n"
        elif isinstance(value, dict):  # 处理字典情况
            cfg_text += f"{indent_str}{key}\n{indent_str}{{\n"
            cfg_text += dict_to_cfg(value, indent + 1)  # 递归处理字典
            cfg_text += f"{indent_str}}}\n"
        else:  # 处理普通键值对
            cfg_text += f"{indent_str}{key} = {value}\n"

    return cfg_text


def modify_dict(d, modifier, name):
    """
    遍历字典，修改其中键值对的键和值。
    """
    if isinstance(d, dict):
        modified_dict = {}
        for key, value in d.items():
            # 修改键和值
            d_name = d["name"] if "name" in d else "unnamed"
            if isinstance(value, (dict, list)):
                ret_dicts = modify_dict(value, modifier, name + "_" + d_name)
                for ret_dict in ret_dicts:
                    ret_dict_name = ret_dict["name"]
                    ret_dict.pop("name")
                    # 新字典赋值
                    modified_dict[
                        "@"
                        + key
                        + f"[{ret_dict_name}]"
                        + ("" if key == "CONTRACT_TYPE" else "")
                    ] = ret_dict
            else:
                new_key, new_value = modifier(key, value, name + "_" + d_name)
                if new_key is not None:
                    modified_dict[new_key] = new_value
        return modified_dict
    elif isinstance(d, list):
        # 如果是列表，递归修改列表中的每一项
        ret_list = [modify_dict(item, modifier, name) for item in d]
        ret_list = [it for it in ret_list if it is not None and len(it) > 1]
        return ret_list


def modify_dict_key(key: str, value: str, name: str):
    if key in [
        "title",
        "description",
        "genericTitle",
        "genericDescription",
        "synopsis",
        "completedMessage",
        "agent",
    ]:
        loc_name = "#" + name + "_" + key
        loc_dic[loc_name] = "暂未翻译 // " + value
        loc_dic_en[loc_name] = value
        return "@" + key, loc_name + " // " + value
    if key == "name":
        return key, value
    return None, None


def create_patch(dic):
    # 创建字典
    global loc_dic, loc_dic_en
    loc_dic = {}
    loc_dic_en = {}
    dic["name"] = ""

    # 补丁字典
    patch_dict = modify_dict(dic, modify_dict_key, "RP1CONTRACT_LOC")
    patch_dict.pop("name")

    # 补丁字典转回patch
    patch = dict_to_cfg(patch_dict)

    return patch


if __name__ == "__main__":
    import os

    folder_path = "./RP-1/Contracts/"

    all_patch = []
    all_loc = []
    all_loc_en = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if root == "./RP-1/Contracts/":
                continue
            if file.endswith(".cfg"):
                file_path = os.path.join(root, file)

                # 读取cfg文件内容
                with open(file_path, "r", encoding="utf-8") as f:
                    cfg_text = f.read()

                dic = cfg_to_dict(cfg_text)
                base_name = dic["CONTRACT_TYPE"][0]["name"]
                sort_key = (
                    int(dic["CONTRACT_TYPE"][0]["sortKey"])
                    if "sortKey" in dic["CONTRACT_TYPE"][0]
                    else (100000)
                )
                patch = create_patch(dic)
                all_patch.append((sort_key, patch))
                all_loc.append((sort_key, loc_dic))
                all_loc_en.append((sort_key, loc_dic_en))

    def merge_dic(all):
        merged_dict = {}
        for d in all:
            merged_dict.update(d)
        return merged_dict

    # 全体patch 按sort排序
    all_patch = [t[1] for t in sorted(all_patch, key=lambda x: x[0])]
    all_loc = [t[1] for t in sorted(all_loc, key=lambda x: x[0])]
    all_loc_en = [t[1] for t in sorted(all_loc_en, key=lambda x: x[0])]

    # 合并loc
    all_loc = merge_dic(all_loc)
    all_loc_en = merge_dic(all_loc_en)

    # 转回cfg
    all_patch = "\n".join(all_patch)
    all_loc = dict_to_cfg({"Localization": {"zh-cn": all_loc}})
    all_loc_en = dict_to_cfg({"Localization": {"en-us": all_loc_en}})

    with open("temp.cfg", "w", encoding="utf-8") as f:
        f.write(all_patch)
    with open("temp_loc.cfg", "w", encoding="utf-8") as f:
        f.write(all_loc)
    with open("temp_loc_en.cfg", "w", encoding="utf-8") as f:
        f.write(all_loc_en)

    print("运行完成")
