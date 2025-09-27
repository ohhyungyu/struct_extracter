from pathlib import Path
import re
import pdb


DEBUG_LOC = "packages/xnu/"
RELEASE_LOC = " 수정 필 요 **"

# 헤더파일 경로 모두 추출
def HeaderFileLoc_extract() -> list:
    root = Path(RELEASE_LOC).resolve()
    # root = Path(DEBUG_LOC).resolve()
    results: list[str] = []

    # pathlib.Path.rglob('*')는 심볼릭 링크를 따라가지 않음(무한 루프 방지에 유리)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        
        s = str(p.relative_to(root).as_posix())
        if '.h' in s and not 'test' in s:
            results.append(str(p.as_posix()))

    ''' Debug
    for _ in results:
        print(_)'''
    return results

# member 변수 정의 추출
def parse_member_declaration(decl):
    decl = decl.strip()
    members = []
    # Check if the member is a struct/union (possibly nested definition or reference)
    if decl.startswith('struct') or decl.startswith('union'):
        brace_index = decl.find('{')
        if brace_index != -1:
            # Nested inline struct/union definition
            parsed = parse_c_declaration(decl)  # recursively parse the inner definition
            member_name = parsed.get('instance') or parsed.get('alias') or parsed.get('name')
            members.append({
                'type': parsed['type'] + ((" " + parsed['name']) if parsed['name'] else ""),
                'name': member_name,
                'bitsize': None,
                'unionTrue': parsed['unionTrue'],
                'structTrue': parsed['structTrue'],
                'members': parsed.get('members')
            })
            return members
        else:
            # It's a reference to an existing struct/union type (no braces)
            tokens = decl.replace(';','').split()
            base_type = " ".join(tokens[:-1])  # e.g. "struct t"
            var_name = tokens[-1]
            members.append({
                'type': base_type,
                'name': var_name,
                'bitsize': None,
                'unionTrue': True if tokens[0] == 'union' else False,
                'structTrue': True if tokens[0] == 'struct' else False,
                'members': None
            })
            return members
    # Not a struct/union, so it's a normal field (could be multiple, separated by commas)
    # Split by commas at top level (ignore commas in any potential parentheses)
    parts = []
    depth = 0
    current = ""
    for ch in decl:
        if ch == ',' and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
    if current.strip():
        parts.append(current.strip())
    # Determine the base type from the first part
    base_type = None
    first_name = None
    first_bits = None
    first_part = parts[0]
    if ':' in first_part:  # bit-field syntax detected
        col_index = first_part.index(':')
        # Everything after ':' is the bit-field width (constant expression):contentReference[oaicite:2]{index=2}
        bits_str = first_part[col_index+1:].strip()
        try:
            first_bits = int(bits_str)
        except ValueError:
            first_bits = bits_str  # in case it's not a simple integer
        before_colon = first_part[:col_index].strip()
        # Split type vs name in the part before colon
        idx = before_colon.rfind(' ')
        if idx != -1:
            base_type = before_colon[:idx].strip()
            first_name = before_colon[idx+1:].strip()
        else:
            # Edge case: no space (unlikely, as there should be a type and a name)
            base_type = before_colon
            first_name = None
    else:
        # No bitfield in first part; split last token as name
        idx = first_part.rfind(' ')
        if idx != -1:
            base_type = first_part[:idx].strip()
            first_name = first_part[idx+1:].strip()
        else:
            base_type = first_part
            first_name = None
    # Process each declaration part
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        name = None
        bitsize = None
        if i == 0:
            # First part may have been handled above
            name = first_name
            bitsize = first_bits
        else:
            # Subsequent parts use the same base_type
            if ':' in part:
                col_index = part.index(':')
                bits_str = part[col_index+1:].strip()
                try:
                    bitsize = int(bits_str)
                except ValueError:
                    bitsize = bits_str
                name = part[:col_index].strip()
            else:
                name = part
            # Handle pointer notation '*' at the start of name by appending to type
            if name.startswith('*'):
                base_type = base_type + " *"
                name = name.lstrip('*').strip()
            # Handle array notation by stripping dimensions from name (optional)
            if '[' in name:
                name = name.split('[')[0].strip()
        members.append({
            'type': base_type,
            'name': name,
            'bitsize': bitsize,
            'unionTrue': True if base_type.split()[0] == 'union' else False,
            'structTrue': True if base_type.split()[0] == 'struct' else False
        })
    return members

# struct 추출
def parse_c_declaration(code):
    code = code.strip()
    if code.endswith(';'):
        code = code[:-1].strip()  # remove trailing semicolon
    result = {}
    # Check for typedef
    is_typedef = code.startswith('typedef')
    if is_typedef:
        code_body = code[len('typedef'):].strip()
    else:
        code_body = code
    # Check for struct/union definitions (braces present)
    brace_index = code_body.find('{')
    if brace_index != -1:
        # It's a struct/union definition
        header = code_body[:brace_index].strip()   # e.g. "struct test" or "union U"
        # Determine struct vs union and any tag name
        tokens = header.split()
        kind = tokens[0]  # "struct" or "union"
        tag_name = tokens[1] if len(tokens) > 1 else None
        # Find matching closing brace for the first '{'
        brace_count = 0
        match_index = None
        for i, ch in enumerate(code_body[brace_index:], start=brace_index):
            if ch == '{': 
                brace_count += 1
            elif ch == '}':
                brace_count -= 1
                if brace_count == 0:
                    match_index = i
                    break
        inner_content = code_body[brace_index+1:match_index]  # content inside the braces
        after_brace = code_body[match_index+1:].strip()  # text after the closing brace
        alias_name = None
        instance_name = None
        if after_brace:
            # If there's text after '}', it could be an alias name (for typedef) or an instance name
            # Take the first word as the name (exclude any trailing array brackets or pointers for simplicity)
            m = re.match(r'([A-Za-z_]\w*)', after_brace)
            if m:
                trailing_name = m.group(1)
                if is_typedef:
                    alias_name = trailing_name
                else:
                    instance_name = trailing_name
        # Fill in the result dictionary for this struct/union
        result['type'] = kind
        result['name'] = tag_name if tag_name else None
        result['alias'] = alias_name if alias_name else None
        result['typedef'] = is_typedef
        result['structTrue'] = (kind == 'struct')
        result['unionTrue'] = (kind == 'union')
        if instance_name:
            result['instance'] = instance_name  # name of the instance (if a variable is declared along with definition)
        # Parse inner members recursively
        member_lines = []
        buf = ""
        depth = 0
        for ch in inner_content:
            if ch == ';' and depth == 0:
                # end of a top-level member declaration
                member_lines.append(buf.strip())
                buf = ""
            else:
                buf += ch
                if ch == '{': 
                    depth += 1
                elif ch == '}':
                    depth -= 1
        if buf.strip():
            member_lines.append(buf.strip())  # last member (if not already added)
        # Parse each member declaration line
        members = []
        for line in member_lines:
            if line:  # non-empty
                members.extend(parse_member_declaration(line))
        result['members'] = members
    else:
        # No braces - this could be a typedef for an existing type, or a simple declaration
        tokens = code_body.replace(';','').split()
        if is_typedef:
            # e.g. "struct X Y" or "int MyInt"
            alias_name = tokens[-1]
            base_type = " ".join(tokens[:-1])
            result['type'] = base_type
            result['alias'] = alias_name
            result['name'] = None
            result['typedef'] = True
            result['structTrue'] = base_type.startswith('struct')
            result['unionTrue'] = base_type.startswith('union')
            result['members'] = None  # alias to a simple type or existing struct (no new members defined here)
        else:
            # A non-typedef declaration without braces (likely a variable declaration of a struct/union)
            var_name = tokens[-1]
            base_type = " ".join(tokens[:-1])
            result['type'] = base_type
            result['name'] = None
            result['alias'] = None
            result['typedef'] = False
            result['structTrue'] = base_type.startswith('struct')
            result['unionTrue'] = base_type.startswith('union')
            result['instance'] = var_name
            result['members'] = None
    return result


def merge_backslash_lines(code: str) -> str:
    """
    백슬래시(\\)로 줄이 이어진 경우 다음 줄과 합쳐 하나의 논리적인 코드 라인으로 만든다.
    (예: 매크로 정의에서 \\ 로 줄을 바꾼 경우 등)
    """
    merged = []
    i = 0
    n = len(code)
    while i < n:
        if code[i] == '\\':
            # 현재 문자가 '\'이고 다음 문자가 줄바꿈이라면 둘 다 건너뛰어 다음 줄과 연결
            if i + 1 < n and code[i+1] == '\n':
                i += 2
                continue
            if i + 2 < n and code[i+1] == '\r' and code[i+2] == '\n':  # CRLF 지원
                i += 3
                continue
            # '\' 뒤에 바로 개행이 없다면 일반 문자로 처리
            merged.append(code[i])
            i += 1
        else:
            merged.append(code[i])
            if code[i] == '\n':
                # 줄바꿈은 그대로 추가 (백슬래시로 이은 경우는 위에서 처리됨)
                pass
            i += 1
    return ''.join(merged)


def remove_comments(code: str) -> str:
    """
    코드 문자열에서 C/C++ 주석(// 한 줄 주석, /* 블록 주석 */)을 제거한다.
    문자열 리터럴 내부의 //, /* */ 패턴은 보존하며, 주석은 모두 빈 칸 혹은 줄바꿈으로 치환.
    """
    result = []
    i = 0
    n = len(code)
    in_single_quote = False   # 문자 리터럴 내부 여부
    in_double_quote = False   # 문자열 리터럴 내부 여부
    in_line_comment = False   # // 주석 모드
    in_block_comment = False  # /* */ 주석 모드
    last_char = ''            # 직전 문자 (이스케이프 처리 확인용)

    while i < n:
        ch = code[i]
        # 한 줄 주석 종료: 새 줄을 만나면 한 줄 주석 모드 해제
        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
                result.append(ch)  # 줄바꿈은 유지
            i += 1
            continue
        # 블록 주석 처리: '*/'를 만나면 주석 끝
        if in_block_comment:
            if ch == '*' and i + 1 < n and code[i+1] == '/':
                in_block_comment = False
                i += 2
                continue  # '*/' 건너뜀
            i += 1
            continue

        # 현재 주석 모드가 아니고, 문자/문자열 리터럴도 아닌 상태
        if not in_single_quote and not in_double_quote:
            # "//" 한 줄 주석 시작
            if ch == '/' and i + 1 < n and code[i+1] == '/':
                in_line_comment = True
                i += 2  # 주석 시작 기호 "//" 넘김
                continue
            # "/*" 블록 주석 시작
            if ch == '/' and i + 1 < n and code[i+1] == '*':
                in_block_comment = True
                i += 2  # 주석 시작 "/*" 넘김
                continue

        # 문자 리터럴 시작/종료
        if ch == "'" and not in_double_quote:
            # 이전 문자가 백슬래시가 아니고 현재 싱글쿼트 모드가 아니면 문자 리터럴 시작
            if not in_single_quote:
                in_single_quote = True
            # 이미 문자 리터럴 내부이고 이전 문자가 이스케이프가 아니면 문자 리터럴 종료
            elif last_char != '\\':
                in_single_quote = False
            result.append(ch)
            last_char = ch
            i += 1
            continue

        # 문자열 리터럴 시작/종료
        if ch == '"' and not in_single_quote:
            if not in_double_quote:
                in_double_quote = True
            elif last_char != '\\':
                in_double_quote = False
            result.append(ch)
            last_char = ch
            i += 1
            continue

        # 위에서 주석/문자열 처리를 모두 거른 일반 문자 처리
        result.append(ch)
        last_char = ch
        i += 1

    return ''.join(result)


def parse_header_code(header_code: str, defined_macros: list[str]) -> tuple[list[str], list[str], list[tuple[str, str | None]]]:
    """
    주어진 C 헤더파일 코드(header_code)와 사전에 정의된 매크로 목록(defined_macros)을 입력으로 받아,
    - 함수 프로토타입 리스트,
    - 구조체 정의 코드 블록 리스트,
    - #define으로 정의된 매크로 상수 리스트 (이름, 값) 튜플들을 반환한다.
    """
    # 1. 백슬래시로 연결된 줄 병합 (매크로 정의의 다중 라인 등 처리) 및 주석 제거
    code = remove_comments(merge_backslash_lines(header_code))

    # 2. 조건부 컴파일 처리: 유효하지 않은 코드 블록은 제거
    active_defines = set(defined_macros)  # 현재 정의된 매크로 집합 (초기값은 입력 리스트)
    active_code_lines: list[str] = []     # 조건을 만족하여 살아남은 코드 줄들
    out_macros: list[tuple[str, str | None]] = []  # 추출된 매크로 상수 리스트

    # 스택을 이용하여 조건문 중첩 처리
    condition_stack: list[bool] = []   # 각 조건부 블록의 현재 활성 상태
    true_taken_stack: list[bool] = []  # 각 조건부 블록에서 이미 참인 분기가 있었는지 여부

    # 조건식 평가 함수 (defined, !defined, 상수치 등을 처리)
    def eval_condition(expr: str) -> bool:
        expr = expr.strip()
        # defined 매크로 치환
        expr = expr.replace("defined(", "defined (")  # 토큰 분리를 위해 괄호 뒤 공백처리
        tokens = expr.split()
        # C 전처리기에서 정의되지 않은 식별자는 0으로 취급되므로, 토큰 단위로 처리
        eval_tokens: list[str] = []
        skip_next = False
        for i, token in enumerate(tokens):
            if skip_next:
                skip_next = False
                continue
            if token == "defined":
                # 토큰 다음에 오는 매크로 이름 확인
                if i + 1 < len(tokens) and tokens[i+1].startswith("("):
                    # 정의식 형태: defined (MACRO)
                    macro_name = tokens[i+1].strip("()")
                    skip_next = True
                else:
                    # 정의식 형태: defined MACRO
                    macro_name = tokens[i+1] if i + 1 < len(tokens) else ""
                    skip_next = True
                eval_tokens.append("True" if macro_name in active_defines else "False")
            elif token.isidentifier():
                # 식별자는 정의 여부에 따라 True/False로, 정의되어 있다면 True (0이 아닌 값)로 간주
                eval_tokens.append("True" if token in active_defines else "False")
            else:
                # 숫자나 연산자는 그대로 추가 (예: 0, 1, &&, ||, ! 등)
                # C의 &&, ||을 파이썬의 and, or로, !을 not으로 변경
                if token == "&&":
                    eval_tokens.append("and")
                elif token == "||":
                    eval_tokens.append("or")
                elif token == "!":
                    eval_tokens.append("not")
                else:
                    eval_tokens.append(token)
        # 토큰들을 다시 하나의 표현식 문자열로 결합
        eval_expr = " ".join(eval_tokens)
        try:
            return bool(eval(eval_expr))
        except Exception:
            return False
        
    # 코드 라인을 순회하며 조건 처리
    for line in code.splitlines():
        stripped = line.lstrip()  # 좌측 공백 제거하여 디렉티브 확인
        parent_active = all(condition_stack) if condition_stack else True  # 현재까지 모든 상위 조건이 유효한지

        # include 는 제거
        if stripped.startswith("#include") or stripped.startswith("#import"):
            continue
        # 조건부 컴파일 지시문 처리
        if stripped.startswith("#ifdef"):
            macro = stripped.split()[1] if len(stripped.split()) > 1 else ""
            cond = macro in active_defines
            condition_stack.append(parent_active and cond)
            true_taken_stack.append(parent_active and cond)
            continue  # 해당 지시문은 출력하지 않음
        if stripped.startswith("#ifndef"):
            macro = stripped.split()[1] if len(stripped.split()) > 1 else ""
            cond = macro not in active_defines
            condition_stack.append(parent_active and cond)
            true_taken_stack.append(parent_active and cond)
            continue
        if stripped.startswith("#if") and not stripped.startswith("#ifdef") and not stripped.startswith("#ifndef"):
            condition = stripped[len("#if"):].strip()
            cond = eval_condition(condition) if parent_active else False
            condition_stack.append(parent_active and cond)
            true_taken_stack.append(parent_active and cond)
            continue
        if stripped.startswith("#elif"):
            if not condition_stack:
                continue  # 대응하는 #if가 없는 경우
            # 이전까지 참인 분기가 없고 상위 조건이 활성인 경우에만 평가
            cond = False
            if not true_taken_stack[-1] and parent_active:
                condition = stripped[len("#elif"):].strip()
                cond = eval_condition(condition)
            condition_stack[-1] = parent_active and cond
            if cond and parent_active:
                true_taken_stack[-1] = True
            continue
        if stripped.startswith("#else"):
            if not condition_stack:
                continue
            # 이전에 참인 분기가 없고 상위 조건 유효 시에만 실행
            cond = parent_active and not true_taken_stack[-1]
            condition_stack[-1] = cond
            true_taken_stack[-1] = True  # else 분기는 이전에 참인 분기가 없으면 실행됨을 표시
            continue
        if stripped.startswith("#endif"):
            if not condition_stack:
                continue
            condition_stack.pop()
            true_taken_stack.pop()
            continue

        # 매크로 정의 처리 (#define, #undef 등) - 상위 조건이 참일 때만 반영
        if stripped.startswith("#define") and parent_active:
            # "#define NAME value" 형식 처리 (함수형 매크로는 제외)
            tokens = stripped.split(maxsplit=2)  # ["#define", "NAME", "value..."]
            if len(tokens) >= 2:
                name = tokens[1]
                # 함수형 매크로 확인: 매크로 이름 바로 뒤에 '('가 붙으면 함수 매크로
                is_function_like = name.endswith("(") or (len(tokens) >= 3 and tokens[2].strip().startswith("("))
                if not is_function_like:
                    # 값이 있는지 확인 (없으면 None)
                    value = None
                    if len(tokens) == 3:
                        # tokens[2]에 매크로 값 전체가 들어있음
                        val_str = tokens[2].strip()
                        value = val_str if val_str != "" else None
                    out_macros.append((name, value))
                    active_defines.add(name)  # 매크로를 정의된 집합에 추가
            continue  # 매크로 정의 행 자체는 출력 리스트에 추가하지 않음

        if stripped.startswith("#undef") and parent_active:
            tokens = stripped.split()
            if len(tokens) > 1:
                macro = tokens[1]
                if macro in active_defines:
                    active_defines.remove(macro)
            continue

        # 조건부에 따라 활성화된 일반 코드 줄만 저장
        if parent_active:
            active_code_lines.append(line)

    active_code = "\n".join(active_code_lines)    

    # 3. 구조체 정의 블록 추출
    structs: list[str] = []
    struct_spans: list[tuple[int, int]] = []  # 구조체 정의의 (시작 인덱스, 끝 인덱스) 범위 (코드 문자열 내)
    brace_depth = 0
    i = 0
    n = len(active_code)

    # regex 패턴 저장
    # struct name {
    RE_STRUCT_NAMED = re.compile(r'^\s*struct\s+[A-Za-z0-9_]\w*\s*\{')
    # struct {
    RE_STRUCT_ANON = re.compile(r'^\s*struct\s*\{')
    while i < n:
        # 전역 범위(brace_depth == 0)에서 "struct" 키워드를 찾음
        # 수정 전
        # if brace_depth == 0 and code_no_comments.startswith("struct", i) \
        #    and (i == 0 or not (code_no_comments[i-1].isalnum() or code_no_comments[i-1] == '_')):
        # 수정 후 typedef 키워드가 붙은 struct 까지 탐지 완료
        _3_line = active_code[i: i+ active_code[i:].find('\n')]
        if brace_depth == 0 and \
            ( \
             (active_code.startswith("typedef", i) and "struct" in active_code[i:i+15]) \
                or \
                active_code.startswith("struct", i) \
            ) \
           and (i == 0 or not (active_code[i-1].isalnum() or active_code[i-1] == '_')) and \
           (RE_STRUCT_NAMED.search(_3_line) or RE_STRUCT_ANON.search(_3_line)):

            # 구조체 정의 후보 발견 (키워드 "struct")
            j = i + len("struct")
            # struct 키워드 뒤 공백 및 토큰 건너뜀 (이름 또는 속성 등)
            while j < n and active_code[j].isspace():
                j += 1
            # struct 정의인지 확인하기 위해 '{' 찾기
            brace_open_idx = -1
            k = j
            while k < n:
                if active_code[k] == '{':
                    brace_open_idx = k
                    break
                if active_code[k] == ';':
                    # 세미콜론이 중간에 나오면 구조체 정의가 아닌 전방 선언 "struct Name;"로 판단
                    break
                k += 1
            if brace_open_idx != -1:
                # '{'를 찾았다면 구조체 정의 시작
                brace_depth = 1
                k = brace_open_idx + 1
                while k < n and brace_depth > 0:
                    # 내부 중첩된 중괄호까지 모두 처리하여 매칭되는 '}' 찾기
                    if active_code[k] == '{':
                        brace_depth += 1
                    elif active_code[k] == '}':
                        brace_depth -= 1
                    k += 1
                if brace_depth != 0:
                    # 중괄호 불일치 발생 시 중단
                    break
                brace_close_idx = k - 1  # 매칭되는 '}' 위치
                # 구조체 정의 끝의 세미콜론 포함 범위 산정
                l = brace_close_idx + 1
                # 세미콜론 나올 때 까지 l 증가
                while l < n and active_code[l] != ';':
                    l += 1
                if l < n and active_code[l] == ';':
                    l += 1  # 세미콜론까지 포함
                else:
                    # 만약 세미콜론이 없으면 (비정상 상황) '}'까지만 포함
                    l = brace_close_idx + 1
                # 구조체 전체 정의 코드를 추출
                struct_code_block = active_code[i:l]
                structs.append(struct_code_block.strip())
                struct_spans.append((i, l))
                i = l  # 해당 구조체 블록 이후로 인덱스 이동
                continue
        # 전역이 아닌 경우 중괄호 깊이 조정 (다른 블록 내부 - 예: 함수 정의 등)
        if active_code[i] == '{':
            brace_depth += 1
        elif active_code[i] == '}':
            brace_depth -= 1
            
        i += 1

    # 추출한 구조체 정의 부분을 코드에서 제거하여 이후 단계(함수 프로토타입 탐색)에 영향 없게 함
    code_outside_structs = active_code
    if struct_spans:
        # 구조체 정의 영역을 빈 문자열로 대체
        code_outside_list = []
        last_end = 0
        for start, end in struct_spans:
            code_outside_list.append(code_outside_structs[last_end:start])
            last_end = end
        code_outside_list.append(code_outside_structs[last_end:])  # 마지막 부분 추가
        code_outside_structs = "".join(code_outside_list)

    # 4. 함수 프로토타입 추출
    func_prototypes: list[str] = []
    brace_depth = 0
    stmt_start = 0
    n2 = len(code_outside_structs)
    for idx, ch in enumerate(code_outside_structs):
        # 중괄호 깊이 추적 (함수 구현이나 기타 블록 무시)
        if ch == '{':
            brace_depth += 1
        elif ch == '}':
            if brace_depth > 0:
                brace_depth -= 1
        elif ch == ';' and brace_depth == 0:
            # 세미콜론 만났을 때 전역 범위라면 하나의 문장 종료
            stmt_end = idx
            stmt = code_outside_structs[stmt_start:stmt_end+1].strip()
            stmt_start = idx + 1  # 다음 문 시작 위치 설정
            # 세미콜론으로 끝나는 선언문 중 함수 프로토타입 판별
            if '(' in stmt:
                # 제외 조건: typedef 선언, struct/union/enum 선언 등은 함수 프로토타입이 아님
                if stmt.startswith("typedef") or stmt.startswith("struct") \
                   or stmt.startswith("union") or stmt.startswith("enum"):
                    pass
                else:
                    # 함수 포인터 선언 판별: 반환 타입 부분에 "(*" 패턴이 있는 경우 제외
                    first_paren = stmt.find('(')
                    # 첫 '(' 이후에 바로 '*'가 나오면 함수 이름이 아니라 함수 포인터 선언으로 판단
                    pos = first_paren + 1
                    while pos < len(stmt) and stmt[pos].isspace():
                        pos += 1
                    if pos < len(stmt) and stmt[pos] == '*':
                        # 함수 포인터 변수 또는 타입 선언 -> 제외
                        pass
                    else:
                        func_prototypes.append(stmt)
    return func_prototypes, structs, out_macros


if __name__ == "__main__":
    headers = HeaderFileLoc_extract()

    print(headers)
