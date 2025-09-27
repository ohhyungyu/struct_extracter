import pdb
from pathlib import Path
import re

DEBUG_LOC = "packages/xnu/"
RELEASE_LOC = "../packages/xnu/"

# 헤더파일 경로 모두 추출
def HeaderFileLoc_extract() -> list:
    root = Path(RELEASE_LOC).resolve()
    # root = Path(DEBUG_LOC).resolve()
    results: list[str] = []

    # pathlib.Path.rglob('*')는 심볼릭 링크를 따라가지 않음(무한 루프 방지에 유리)
    for p in root.rglob("*"):
        # 필터링
        if not p.is_file():
            continue
        
        s = str(p.relative_to(root).as_posix())
        if '.h' in s and not 'test' in s:
            results.append(str(p.as_posix()))

    ''' Debug
    for _ in results:
        print(_)
        
    '''
    pdb.set_trace()
    return results

if __name__ == '__main__':
    result = HeaderFileLoc_extract()
