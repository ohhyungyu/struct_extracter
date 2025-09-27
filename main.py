from module import XnuSrcToStruct
import pdb

DEFINED_APPLE = [
    'MACH_KERNEL_PRIVATE',"__ARM64__","__arm64__","__LP64__","__APPLE__",
    "APPLE","__MACH__","KERNEL","KERNEL_PRIVATE","XNU_KERNEL_PRIVATE",
    "MACH_KERNEL_PRIVATE","BSD_KERNEL_PRIVATE","IOKIT_KERNEL_PRIVATE",
    "LIBKERN_KERNEL_PRIVATE","PRIVATE","XNU_KERN_EVENT_DATA_IS_VLA",
    "XNU_BUILT_WITH_BTI","XNU_TARGET_OS_OSX","ARM64_BOARD_CONFIG_T8101",
    "ARM64_BOARD_CONFIG_T8103","ARM64_BOARD_CONFIG_T6000","ARM64_BOARD_CONFIG_T6020",
    "ARM64_BOARD_CONFIG_T8112","ARM64_BOARD_CONFIG_T6030","ARM64_BOARD_CONFIG_T6031",
    "ARM64_BOARD_CONFIG_T8122_T8130","ARM64_BOARD_CONFIG_T8132","ARM64_BOARD_CONFIG_VMAPPLE",
    "CONFIG_AUDIT","CONFIG_MACF","CONFIG_DTRACE","CONFIG_COALITIONS",
    "CONFIG_PROC_UUID_POLICY","CONFIG_SCHED_TRADITIONAL","CONFIG_SCHED_FIXEDPRIORITY",
    "CONFIG_SCHED_GRRR","CONFIG_SCHED_PROTO","SECURE_KERNEL","CONFIG_KDP_INTERACTIVE",
    "CONFIG_KTRACE","NFS_CLIENT","NFS_SERVER","SOCKETS","NECP","DRIVERKIT"
]
HeaderFile_Name = XnuSrcToStruct.HeaderFileLoc_extract()
Rf_s = open("result/STRUCT/result", 'w')
Rf_d = open("result/DEFINE/result", 'w')
Rf_f = open('result/ENUM_FUNC/result', 'w')


for _HN in HeaderFile_Name:
    with open(f"{_HN}", 'rt', encoding='UTF8') as f:
        #try : 
        FullCode = f.read()
        # except UnicodeDecodeError :
        #     pdb.set_trace()
    result = XnuSrcToStruct.parse_header_code(FullCode, DEFINED_APPLE)

    for _Result in result[1]:
        Rf_s.write(_Result)
        Rf_s.write('\n')
    for _Result in result[2]:
        Rf_d.write(f"{_Result[0]} {_Result[1]}")
        Rf_d.write('\n')
    for _Result in result[0]:
        Rf_f.write(_Result)
        Rf_f.write('\n')

Rf_s.close()
Rf_d.close()
Rf_f.close()

print("공백 매우 지우기 시작")
with open('result/STRUCT/result', 'r') as f:
    FS = f.read()

MAX_FS = len(FS)
i = 0
FIXED = ''
while i < MAX_FS:
    if FS[i] == '\n' and \
        i + 2 < MAX_FS and \
        FS[i+1] == '\t' and \
        FS[i+2] == '\n':
        i += 1
    else :
        FIXED += FS[i]
    i += 1

with open("result/STRUCT/fixed", 'w') as f:
    f.write(FIXED)         

print('done')