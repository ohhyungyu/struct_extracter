from module import XnuSrcToStruct
import pdb

STRUCT = 1
DEFINE = 2
TYPEDEFENUM = 0
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
    "CONFIG_KTRACE","NFS_CLIENT","NFS_SERVER","SOCKETS","NECP","DRIVERKIT", 
    "CONFIG_FREEZE", "CONFIG_MEMORYSTATUS", "CONFIG_NEXUS_FLOWSWITCH", "__APPLE_API_PRIVATE",
    "SYSCTL_DEF_ENABLED", 
]
HeaderFile_Name = XnuSrcToStruct.HeaderFileLoc_extract()
Rf_s = open("result/STRUCT/result_mac", 'w')
# Rf_f = open('result/ENUM_FUNC/result_mac', 'w')
print("HEADER GOOD")

RESULT_DEFINED = dict()

for _HN in HeaderFile_Name:
    print(f"{_HN}")

    # utf-8-sig
    with open(f"{_HN}", 'rt', encoding="utf-8", errors="replace") as f:
        #try : 
        FullCode = f.read()
        # except UnicodeDecodeError :
        #     pdb.set_trace()
    result = XnuSrcToStruct.parse_header_code(FullCode, DEFINED_APPLE)

    for _Result in result[STRUCT]:
        _Result = _Result.replace('\xa9', '')
        Rf_s.write(_Result)
        Rf_s.write('\n')
    RESULT_DEFINED.update(result[DEFINE])


Rf_s.close()
print("공백 매우 지우기 시작")
with open('result/STRUCT/result_mac', 'r') as f:
    FS = f.read()

with open("result/STRUCT/fixed_mac", 'w') as f:
    f.write(XnuSrcToStruct.Delete_for_Pretty(FS))         

print("MACRO INTO STRUCT")

with open('result/STRUCT/fixed_mac', 'r') as f:
    FullCode = f.read()

Really_Fixed, unsolved = XnuSrcToStruct.Find_and_insert_macro_into_struct(FullCode, RESULT_DEFINED)

Reallyyy_Fixed, unresolved = XnuSrcToStruct.replace_bracket_constants(Really_Fixed, RESULT_DEFINED)

with open('result/STRUCT/really_fixed.h', 'w') as f:
    f.write(Reallyyy_Fixed)

with open('result/STRUCT/unresolved', 'w') as f:
    for _ in unresolved:
        f.write(_ + '\n')
    
# print(unresolved)
# pdb.set_trace()