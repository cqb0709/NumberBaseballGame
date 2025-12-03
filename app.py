import streamlit as st
import time
import re
import random

from game_multiproc import NumberBaseballGame


def main():
    
    # --- 1. 세션 상태 초기화 ---
    def init_session_state():
        default_values = {
            'page': 'main',                         #페이지 상태
            'messages': [],                         #채팅 기록
            'game_level': 3,                        #레벨 변수
            'show_exit_confirm': False,             #홈으로 돌아가기 확인창 상태
            'input_disabled': False,                #채팅창 비활성화 상태 관리
            'autoplay_checked': True,               #체크박스 상태 관리1
            'player_mode_checked': False,           #체크박스 상태 관리2
            'player_action': 'Attack',              #플레이어 모드 액션 (ATk / DFS) 상태 관리
            'manual_input_value': "",               #AUTOPLAY용 정답 입력 창
            'active_mode': None,                    #현재 실행중인 모드 상태
            
            # game_instance는 start_game에서 생성되므로 여기서 None으로 두거나 생략 가능
        }
        
        for key, value in default_values.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
        # 안전장치: 레벨 최소값 보정
        if st.session_state.game_level < 3:
            st.session_state.game_level = 3    
    
    # 초기화 함수 실행
    init_session_state()
    
    # --- 2. CSS 스타일 정의 (말풍선 디자인) ---
    def load_css():
        st.markdown("""
        <style>
        
            /* 1. 메인 컨텐츠 영역의 상단 여백 제거  */
            .block-container {
                padding-top: 1rem !important; /* 기본값이 6rem 정도인데 이를 1rem으로 줄임 */
                padding-bottom: 0rem !important;
            }
            
            /* (선택사항) Streamlit 기본 헤더(햄버거 메뉴, Running 아이콘) 숨기기 
               - 이걸 적용하면 버튼이 진짜 맨 위로 올라갑니다. 
               - 개발 중에는 불편할 수 있으니 필요시 주석 처리하세요. */
            
            header {
                visibility: hidden;
            }
            
            /* 버튼 중앙 정렬을 위한 스타일 */
            .stButton > button {
                display: block;
                margin-left: auto;
                margin-right: auto;
                width: 150px; /* 버튼 너비 설정 (선택사항) */
            }
            
            /* 각 메시지 줄은 100% 너비를 차지하며 Flexbox 사용 */
            .message-row {
                display: flex;
                width: 100%;
                margin-bottom: 10px;
                align-items: center;
            }
            
            /* 사용자(나) : 오른쪽 정렬 */
            .user-row {
                justify-content: flex-end;
            }
            .user-bubble {
                background-color: #FEE500;
                color: black;
                padding: 10px 15px;
                border-radius: 15px;
                border-top-right-radius: 0;
                max-width: 70%;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }
            
            /* 봇(컴퓨터) : 왼쪽 정렬 */
            .bot-row {
                justify-content: flex-start;
            }
            .bot-bubble {
                background-color: #EAEAEA;
                color: black;
                padding: 10px 15px;
                border-radius: 15px;
                border-top-left-radius: 0;
                max-width: 70%;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            }
            
            /* [추가] 멈추지 않는 CSS 로딩 애니메이션 */
            .loader {
                border: 5px solid #f3f3f3; /* 회색 배경 */
                border-top: 5px solid #3498db; /* 파란색 회전부 */
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite; /* 브라우저가 직접 돌림 */
                margin: auto; /* 중앙 정렬 */
            }
    
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
        """, unsafe_allow_html=True)
    
    
    # --- 3. 게임 로직 함수 분리 ---
    
    def logic_autoplay():
        """AUTOPLAY 모드 로직"""
        game = st.session_state.game_instance
        target = st.session_state.manual_input_value
        
        # [핵심 2] 중단 조건 함수 정의 (Lambda 함수)
        # 현재 페이지가 'chat'이 아니거나, 모드가 AUTOPLAY가 아니면 멈춥니다.
        should_stop = lambda: st.session_state.page != 'chat'
        
    
        for msg in game.play_game(target, stop_callback=should_stop):
            
            # 루프 도중이라도 사용자가 홈으로 나갔다면 즉시 중단
            if should_stop():
                break
                
            st.session_state.messages.append({"role": "assistant", "content": msg})
            
            st.markdown(f"""
            <div class="message-row bot-row">
                <div class="bot-bubble">{msg}</div>
            </div>
            """, unsafe_allow_html=True)
                
            time.sleep(0.05)
            
        return
    
    def logic_player_attack(user_input):
        """PLAYER MODE - ATTACK (사용자가 맞추는 모드)"""
        game = st.session_state.game_instance
        game.guess_count += 1
        # 정답이 없으면(혹시 모를 오류 대비) 재생성
        if not hasattr(game, 'secret_answer'):
            n = st.session_state.game_level
            game.secret_answer = "".join(map(str, random.sample(range(10), n)))
        
        strike, ball = game.check_sb(user_input, game.secret_answer)
        
        if strike == st.session_state.game_level:
            st.session_state.active_mode = 'GAME_OVER'
            return strike, ball, f"🎉 정답입니다! {game.guess_count}회 만에 맞혔습니다. 🎉"
        
        # 사용자가 입력한 user_input(숫자)에 대해 Strike/Ball 판정
        return strike, ball, f"입력하신 숫자 '{user_input}'에 대한 판정 결과: {strike}S {ball}B"
    
    def logic_player_defense(user_input):
        """PLAYER MODE - DEFENSE (컴퓨터가 맞추는 모드)"""
        game = st.session_state.game_instance
        
        # 사용자가 '1s 2b' 처럼 결과를 입력하면, 컴퓨터가 다음 추론을 함
        # 패턴: 숫자 1개 + s또는S + 공백 + 숫자 1개 + b또는B
        # 예: "3s 2b", "1S 0B" (공백은 유동적으로 처리: \s+)
        pattern = r"(\d)\s*[sS]\s+(\d)\s*[bB]"
        match = re.search(pattern, user_input)
        
        if not match:
            return "형식이 잘못되었습니다. '3s 2b' 형태로 입력해주세요."
        
        strike = int(match.group(1))
        ball = int(match.group(2))
        
        # 2. 정답 확인 (사용자가 4s 0b라고 입력했다면 게임 종료)
        if strike == st.session_state.game_level:
            st.session_state.active_mode = 'GAME_OVER'
            return f"🎉 정답입니다! {game.guess_count}회 만에 맞혔습니다. 🎉"
        
        # 3. 후보군 필터링 (핵심 로직)
        # 이전 턴의 추측(game.last_guess)과 사용자의 점수(s, b)를 이용해 불가능한 후보 제거
        last_guess = getattr(game, 'last_guess', None)
        if not last_guess:
            return "⛔ 오류: 이전 추측 정보가 없습니다. 게임을 재시작해주세요."
            
        game.candidates = game.filter_candidates(last_guess, strike, ball)
        
        if not game.candidates:
            st.session_state.active_mode = 'GAME_OVER'
            return "⚠️ 오류: 가능한 후보 숫자가 없습니다. 입력한 S/B에 모순이 있습니다."
            
        # 4. 다음 추측 생성 (AI 연산)
        # 남은 후보가 1개면 바로 정답 선언 가능
        if len(game.candidates) == 1:
            next_guess = game.candidates[0]
            st.session_state.active_mode = 'GAME_OVER'
            return f"🎉 정답은 {next_guess}입니다! {game.guess_count + 1}회 만에 맞혔습니다. 🎉"
        else:
            # 시간이 걸릴 수 있으므로 안내 메시지나 스피너가 필요할 수 있음
            # 하지만 여기서는 blocking 방식으로 처리
            next_guess = game.find_next_best_guess()
            
        # 5. 상태 업데이트
        game.last_guess = next_guess
        game.guess_count += 1
        
        return f"💻 {strike}S {ball}B군요. (남은 후보: {len(game.candidates)}개)\n그렇다면... **{next_guess}** 인가요?"
        
    
    # --- 4. 페이지 함수 ---
    def update_level():
        st.session_state.game_level = st.session_state.level_input
    
    # 체크박스 상호작용 처리
    def handle_player_mode_change():
        # PLAYER MODE가 체크되면, AUTOPLAY 체크박스 체크를 해제함
        if st.session_state.player_mode_checked:
            st.session_state.autoplay_checked = False
        
    def handle_autoplay_change():
        # AUTOPLAY가 체크되면, PLAYER MODE 체크박스 체크를 해제함
        if st.session_state.autoplay_checked:
            st.session_state.player_mode_checked = False
    
    # 공격/방어 버튼 선택 로직
    def set_player_action(action):
        st.session_state.player_action = action
    
    def go_home():
        st.session_state.page = 'main'
        st.session_state.messages = []
        st.session_state.show_exit_confirm = False
        st.session_state.input_disabled = False
        
        # 게임 인스턴스 삭제 (메모리 정리)
        if 'game_instance' in st.session_state:
            del st.session_state.game_instance
    
    def start_game():
        st.session_state.page = 'chat'
        st.session_state.show_exit_confirm = False
        st.session_state.input_disabled = False
        st.session_state.messages = [] # 메시지 초기화
        
        # 1. 현재 모드 확정 (active_mode 설정)
        if st.session_state.autoplay_checked:
            st.session_state.active_mode = 'AUTOPLAY_READY'
        elif st.session_state.player_mode_checked:
            if st.session_state.player_action == 'Attack':
                st.session_state.active_mode = 'ATTACK'
            else:
                st.session_state.active_mode = 'DEFENSE'
        
        current_level = st.session_state.game_level
        game = NumberBaseballGame(n=current_level)
        st.session_state.game_instance = game
        
        # 3. 모드별 초기화 로직
        mode = st.session_state.active_mode
        
        if mode == 'AUTOPLAY_READY':
            target = st.session_state.manual_input_value
            st.session_state.messages.append({"role": "assistant", "content": f" AUTOPLAY를 시작합니다! (정답: {target})"})
                
            #st.session_state.messages.append({"role": "assistant", "content": first_msg})
        
        # Defense 모드를 위한 초기화
        elif mode == 'DEFENSE':
            # (1) 후보군 전체 생성 (시간이 좀 걸릴 수 있으므로 안내 메시지 고려)
            game.generate_all_candidates()
            
            # (2) 첫 번째 추측 생성 (예: "0123" 또는 "1234")
            first_guess = game.DIGITS[:current_level]
            
            # (3) 추측을 게임 객체에 저장 (다음 턴에 필터링할 때 써야 함)
            game.last_guess = first_guess
            game.guess_count = 1
            
            # (4) 첫 인사 메시지
            first_msg = f"💻 정답이 **{first_guess}** 인가요?\n결과를 알려주세요 (예: 1s 0b)"
            st.session_state.messages.append({"role": "assistant", "content": first_msg})
        
        # ATTACK 모드일 경우, 여기서 정답을 미리 생성해서 박제합니다.
        elif mode == 'ATTACK':
            # 0~9 중복 없이 n개 뽑아서 문자열로 변환
            digits = random.sample(range(10), current_level)
            secret_number = "".join(map(str, digits))
            
            # 생성된 정답을 게임 객체 안에 저장해둡니다. (이 객체는 홈으로 가기 전까지 유지됨)
            st.session_state.game_instance.secret_answer = secret_number
            
            game.guess_count = 1
            
            print(f"🎯 정답 생성됨: {secret_number}") #디버깅용
    
        # Case A: Assistant 선공 (AUTOPLAY, DEFENSE)
        
        
            
        # Case B: User 선공 (ATTACK)
        # 별도 처리 없음. 메시지 리스트가 빈 상태로 시작하며 사용자가 입력을 기다림.
    
    
    
    # --- 4. 메인 로직 ---
    
    # CSS 로드
    load_css()
    
    # [PAGE 1] 메인 페이지
    if st.session_state.page == 'main':
        st.title("🎮 숫자야구 게임 시작하기")
        
        st.markdown("---")
        
        # 1. 체크박스 영역
        st.write("📢 **게임 모드를 선택하세요:**")
        check_col1, check_col2 = st.columns(2)
        
        # AUTOPLAY 체크박스
        with check_col1:
            # 현재 autoplay가 True면 primary(강조), 아니면 secondary(회색)
            ap_style = "primary" if st.session_state.autoplay_checked else "secondary"
            if st.button("💻 AUTOPLAY", type=ap_style, use_container_width=True):
                st.session_state.autoplay_checked = True
                st.session_state.player_mode_checked = False
                st.rerun()
    
        # PLAYER MODE 체크박스
        with check_col2:
            # 현재 player_mode가 True면 primary, 아니면 secondary
            pm_style = "primary" if st.session_state.player_mode_checked else "secondary"
            if st.button("👤 PLAYER MODE", type=pm_style, use_container_width=True):
                st.session_state.autoplay_checked = False
                st.session_state.player_mode_checked = True
                st.rerun()
            
        st.markdown("---")
        
        # PLAYER MODE 선택 시 -> 공격/방어 버튼 표시
        if st.session_state.player_mode_checked:
            st.write("📢 **행동을 선택하세요:**")
            act_col1, act_col2 = st.columns(2)
            
            # 공격 버튼 (현재 상태가 Attack이면 Primary 색상, 아니면 Secondary)
            with act_col1:
                if st.button(
                    "⚔️ 공격 (Attack)", 
                    use_container_width=True, 
                    type="primary" if st.session_state.player_action == 'Attack' else "secondary"
                ):
                    set_player_action('Attack')
                    st.rerun()
    
            # 방어 버튼 (현재 상태가 Defense이면 Primary 색상)
            with act_col2:
                if st.button(
                    "🛡️ 방어 (Defense)", 
                    use_container_width=True, 
                    type="primary" if st.session_state.player_action == 'Defense' else "secondary"
                ):
                    set_player_action('Defense')
                    st.rerun()
                    
            st.markdown("<br>", unsafe_allow_html=True) # 간격 추가
    
        # [조건 2] AUTOPLAY 선택 시 -> 키보드 숫자 입력창 표시
        if st.session_state.autoplay_checked:
            st.write("⌨️ **자릿수에 맞게 숫자 값을 입력하세요:**")
            st.text_input(
                "Manual Input",
                placeholder="예: 1234",
                key="manual_input_widget",
                label_visibility="collapsed"
            )
            st.markdown("<br>", unsafe_allow_html=True)
        
        
        st.write("난이도(숫자)를 설정하고 시작 버튼을 누르세요.")
        
        col_level_1, col_level_2 = st.columns([1, 4]) 
        
        with col_level_1:
            # - key: "level_input" (위젯 전용 임시 키)
            # - value: st.session_state.game_level (현재 저장된 레벨 값으로 시작)
            # - on_change: 값이 바뀔 때 update_level 함수 실행
            st.number_input(
                "Level", 
                min_value=3, 
                max_value=9, 
                step=1,
                value=st.session_state.game_level, 
                label_visibility="collapsed",
                key="level_input",
                on_change=update_level
            )
    
        with col_level_2:
            if st.button("시작", type="primary", use_container_width=False):
                            
                # [Step 2] AUTOPLAY 모드일 때 유효성 검사
                if st.session_state.autoplay_checked:
                    
                    # 검증용 임시 객체 생성
                    temp_game = NumberBaseballGame(n = st.session_state.game_level)
                    input_val = st.session_state.manual_input_widget
                    is_valid, err_msg = temp_game.validate_answer(input_val)
                    
                    if not is_valid:
                        st.error(f"⛔ {err_msg}") # game.py에서 온 에러 메시지 출력
                    
                    else:
                        # 유효하면 값 저장하고 게임 시작
                        st.session_state.manual_input_value = input_val
                        start_game()
                        st.rerun()
                # [Step 3] PLAYER MODE일 때는 그냥 시작
                else:
                    start_game()
                    st.rerun()
                
    # [PAGE 2] 채팅 페이지
    elif st.session_state.page == 'chat':
        
        # 상단바
        top_col1, top_col2, top_col3 = st.columns([1, 7, 2])
        
        with top_col1:
            if st.button("🏠", help = " Home"):
                st.session_state.show_exit_confirm = not st.session_state.show_exit_confirm
                
                
                if st.session_state.active_mode == 'AUTOPLAY_RUNNING':
                    st.session_state.active_mode = 'GAME_STOPPED'
                
                st.rerun()
        
        with top_col2:
            mode_str = st.session_state.active_mode
            # 게임 종료 상태라면 모드 이름 변경
            if mode_str == 'GAME_OVER':
                mode_str = "GAME OVER"
            elif mode_str == 'GAME_STOPPED': # [추가] 중단 상태 표시
                mode_str = "STOPPED"
                
            st.markdown(f"<h4 style='margin: 0; padding-top: 5px;'>Game Level: {st.session_state.game_level}</h4>", unsafe_allow_html=True)
        
        # 3. 우측: 연산 중단 버튼
        # 오직 '연산 중(AUTOPLAY_RUNNING)'일 때만 버튼을 보여줍니다.
        with top_col3:
            if st.session_state.active_mode in ['AUTOPLAY_RUNNING', 'DEFENSE_CALCULATING']:
                sub_c1, sub_c2 = st.columns([1, 2], gap="small")
                
                with sub_c1:
                    # 파이썬과 무관하게 돌아가는 CSS 로딩바 삽입
                    st.markdown('<div class="loader"></div>', unsafe_allow_html=True)
                
                with sub_c2:
                    if st.button("중단", type="primary", use_container_width=True):
                        st.session_state.active_mode = 'GAME_STOPPED'
                        st.rerun()
            
        
        # 홈 버튼 클릭 시 확인 패널
        if st.session_state.show_exit_confirm:
            with st.container(border=True):
                st.warning("메인 화면으로 돌아가시겠습니까? (기록 초기화)")
                col_y, col_n = st.columns(2)
                if col_y.button("네 (Yes)", use_container_width=True):
                    go_home()
                    st.rerun()
                if col_n.button("아니오 (No)", use_container_width=True):
                    st.session_state.show_exit_confirm = False
                    st.rerun()
            st.markdown("---")
    
        # 채팅 영역과의 거리 벌리기 (Spacer)
        st.markdown('<div class="chat-area-spacer"></div>', unsafe_allow_html=True)
    
        # 채팅 UI 렌더링 (개별 렌더링 방식)
        chat_container = st.container()
        
        with chat_container:
            for msg in st.session_state.messages:
                if msg["role"] == "user":
                    # 사용자 메시지 HTML
                    st.markdown(f"""
                    <div class="message-row user-row">
                        <div class="user-bubble">{msg['content']}</div>
                        
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # 봇 메시지 HTML (여기에 unsafe_allow_html=True가 필수입니다!)
                    st.markdown(f"""
                    <div class="message-row bot-row">
                        <div class="bot-bubble">{msg['content']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # 1. AUTOPLAY 준비 -> 실행
        if st.session_state.active_mode == 'AUTOPLAY_READY':
            # 아주 짧은 텀을 주어 브라우저 랜더링 큐를 비웁니다.
            time.sleep(0.05) 
            st.session_state.active_mode = 'AUTOPLAY_RUNNING'
            st.rerun()
        
        elif st.session_state.active_mode == 'AUTOPLAY_RUNNING':
            
            # 자동 플레이 로직 실행
            logic_autoplay()
            
            # 실행 후 모드를 변경하여 무한 반복 방지 및 입력창 비활성화 유지
            st.session_state.active_mode = 'GAME_OVER'
            st.rerun()
            
        # 사용자가 중단 버튼을 눌렀을 때 메시지 표시
        elif st.session_state.active_mode == 'GAME_STOPPED':
            st.warning("⛔ 사용자에 의해 연산이 중단되었습니다.")
            # 더 이상 연산 로직(logic_autoplay)을 호출하지 않으므로 멈춰있게 됨
        
        # DEFENSE 계산 단계 (화면에 로딩바가 떠있는 상태에서 실행됨)
        elif st.session_state.active_mode == 'DEFENSE_CALCULATING':
            
            # 이전 입력값 가져오기 (임시 저장된 값 사용)
            user_input = st.session_state.temp_defense_input
            
            # 로직 실행
            response = logic_player_defense(user_input)
            
            if response:
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            # 계산 끝나면 다시 대기 상태로 복귀 (또는 게임 오버)
            if st.session_state.active_mode != 'GAME_OVER':
                st.session_state.active_mode = 'DEFENSE'
                
            st.rerun()
    
        # 2. 사용자 입력 (ATTACK / DEFENSE)
        elif st.session_state.active_mode in ['ATTACK', 'DEFENSE', 'DEFENSE_CALCULATING']:
            
            
            # 입력창 (st.chat_input은 그대로 사용)
            if prompt := st.chat_input("메시지를 입력하세요...", disabled=st.session_state.input_disabled):
                # 1. 사용자 메시지 저장
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # 2. 'stop' 감지 로직 (대소문자 무시)
                if prompt.strip().lower() == "stop":
                    st.session_state.input_disabled = True # 입력창 비활성화
                    
                    # 종료 메시지 추가
                    end_msg = " 게임을 종료합니다. (채팅창이 비활성화되었습니다)"
                    st.session_state.messages.append({"role": "assistant", "content": end_msg})
                    
                    st.rerun()
                
                else:
                    response = ""
                    current_mode = st.session_state.active_mode
                    
                        
                    if current_mode == 'ATTACK':
                        game_instance = st.session_state.game_instance
                        is_valid, err_msg = game_instance.validate_answer(prompt)
                        
                        if not is_valid:
                            st.session_state.messages.append({"role": "assistant", "content": err_msg}) # game.py에서 온 에러 메시지 출력
                        else:
                            s, b, response = logic_player_attack(prompt)
                            if s == st.session_state.game_level:
                                st.session_state.messages.append({"role": "assistant", "content": response})
                                st.session_state.active_mode = 'GAME_OVER'
                                st.rerun()
                        
                    elif current_mode == 'DEFENSE':
                        
                        st.session_state.temp_defense_input = prompt # 입력값 임시 저장
                        # 상태 변경 -> 상단 로딩바 표시됨 -> 하단에서 계산 로직 실행
                        st.session_state.active_mode = 'DEFENSE_CALCULATING'
                        st.rerun()
                    
                    
                    
                    # 응답 저장
                    if response:
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    st.rerun()

if __name__ == '__main__':
    main()