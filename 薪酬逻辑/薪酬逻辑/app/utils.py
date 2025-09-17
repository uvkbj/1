BOOL_MAP = {'是': True, '否': False}
BOOL_MAP_REVERSE = {True: '是', False: '否'}
WORK_TYPE_MAP = {'视频相关': False, '拍摄': True}
WORK_TYPE_MAP_REVERSE = {False: '视频相关', True: '拍摄'}

#映射拍摄任务
WORK_OPTIONS = ['策划人、负责人', '脚本', '剪辑', '配音', '拍摄', '灯光、场务、妆造、模特']
def binary_to_labels(bin_str):
    return [label for bit, label in zip(bin_str, WORK_OPTIONS) if bit == '1']
def labels_to_binary(label_list):
    return ''.join(['1' if label in label_list else '0' for label in WORK_OPTIONS])

def map_values_for_display(row):
    row = row.copy()
    for col in row:
        if col in['是否采用','是否原创','好评1','好评2']and row[col] in BOOL_MAP_REVERSE:
            row[col] = BOOL_MAP_REVERSE[row[col]]
        if col == '工作类型':
            row[col] = WORK_TYPE_MAP_REVERSE.get(row[col])
        if col in ['工作1', '工作2']:
            row[col] = ','.join(binary_to_labels(str(row[col])))
    return row

COLUMN_RENAME_MAP = {
    '日期': '日期(年-月-日)',
    '工时': '工时(h)',
    '字数': '最终推文中的字数',
    '拍摄时长': '拍摄时长(h)',
    '整理时长': '整理时长(h)',
    '视频时长':'视频时长(min)',
    '视频单价': '视频单价(￥/min,[60-120])',
    '数量1': '海报、壁纸、尾图数量',
    '好评1': '是否广受好评1',
    '数量2': '可视化设计、H5制作、手绘数量',
    '好评2': '是否广受好评2',
    '工时1': '根据反馈意见修改的工作时长(H)',
    '工时2': '工时(H)',
    '工作1': '有哪些工作由记者团完成',
    '工作2': '你负责了哪些工作',
}

def rename_columns(colunms):
    return [COLUMN_RENAME_MAP.get(col, col) for col in colunms]