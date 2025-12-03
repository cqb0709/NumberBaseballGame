import itertools
import collections

class NumberBaseballGame:
    
    DIGITS = "1234567890" 
    
    def __init__(self, n=4):
        self.scale = n
        self.candidates = []
        self.all_possible_numbers = []
        
    
    def generate_all_candidates(self) -> list[str]:
        """게임 시작 시, 가능한 모든 후보(5040개)를 생성합니다."""
        # 0~9의 숫자 중 4개를 순서대로 나열하는 모든 경우의 수
        all_permutations = itertools.permutations(self.DIGITS, self.scale)
        # ("0", "1", "2", "3") -> "0123" 형태로 변환
        self.candidates = ["".join(p) for p in all_permutations]
        
        self.all_possible_numbers = self.candidates[:]
    
    @staticmethod
    def check_sb(guess: str, answer: str) -> tuple[int, int]:
        """두 숫자(n자리 문자열)를 비교하여 (Strike, Ball)을 반환합니다."""
        strikes = 0
        balls = 0
        
        # 1. 스트라이크 계산 (zip을 쓰면 인덱스 없이 깔끔하게 비교 가능)
        for g, a in zip(guess, answer):
            if g == a:
                strikes += 1
                
        # 2. 볼 계산 (전체 공통 숫자 - 스트라이크 = 볼)
        # set을 사용해 두 숫자에 공통으로 포함된 숫자 개수를 셉니다.
        common_digits = len(set(guess) & set(answer))
        balls = common_digits - strikes
        
        balls = common_digits - strikes
        
        return strikes, balls

    
    def filter_candidates(self, last_guess: str, s_result: int, b_result: int) -> list[str]:
        """
        현재 후보 리스트에서, 마지막 추측 및 S/B 결과와 일치하는
        후보들만 남기고 필터링합니다.
        """
        new_candidates = []
        
        # 현재 리스트의 모든 후보를 하나씩 꺼내어 검사
        for candidate in self.candidates:
            
            # !핵심 로직!
            # "만약 이 candidate가 실제 정답이었다면, 
            #  나의 last_guess가 (s_result, b_result)를 받았을까?"
            
            # check_sb 함수를 사용하되, 'candidate'를 'answer' 자리에 넣습니다.
            (s_check, b_check) = self.check_sb(last_guess, candidate)   #NumberBaseballGame.checksb 사용가능
            
            # 만약 시뮬레이션 결과(s_check, b_check)가
            # 실제 받은 결과(s_result, b_result)와 일치한다면,
            # 이 candidate는 여전히 정답일 가능성이 있습니다.
            if s_check == s_result and b_check == b_result:
                new_candidates.append(candidate)
                
        return new_candidates
    
    
    def find_next_best_guess(self, stop_callback=None) -> str:
        """
        미니맥스 알고리즘을 사용해 최악의 경우를 최소화하는 다음 추측을 찾습니다.
        """
        
        # 최적화: 남은 후보가 2개 이하면, 계산할 필요 없이 첫 번째 후보를 반환합니다.
        # (맞으면 4S, 틀리면 2S 2B 등이 나오고, 그러면 다음 후보가 정답으로 확정됩니다.)
        if len(self.candidates) <= 2:
            return self.candidates[0]
    
        min_worst_case_size = float('inf')  # '최악의 경우 남는 후보 수'의 최소값
        best_guess = ""
    
        # 1. '정보 수집용 질문'은 5040개의 모든 숫자 중에서 찾습니다.
        # 2. 이 'potential_guess'가 현재 후보들을 어떻게 나누는지(partition) 시뮬레이션합니다.
        for potential_guess in self.all_possible_numbers:
            
            if stop_callback and stop_callback():
                # 단순히 return 하는 것보다 Exception을 일으키는 게
                # 호출한 곳(play_game)에서 감지하기 더 확실합니다.
                raise InterruptedError("Game Stopped by User")
            
            partitions = collections.defaultdict(int)  # {(S, B): 개수}} <-- Dictionary
            
            for candidate in self.candidates:
                s, b = self.check_sb(potential_guess, candidate)
                partitions[(s, b)] += 1
                
            if not partitions:
                # 현재 후보 리스트가 비어있는 예외적인 경우
                continue
                
            # 3. 이 추측의 '최악의 경우'(가장 크게 남는 그룹의 크기)를 찾습니다.
            worst_case_size = max(partitions.values())
            
            # 4. '최악의 경우'가 가장 작았던 추측을 갱신합니다.
            if worst_case_size < min_worst_case_size:
                min_worst_case_size = worst_case_size
                best_guess = potential_guess
                
            # 5.  만약 최악의 경우가 같다면?
            # -> 기왕이면 '정답이 될 가능성이 있는 후보(self.candidates)'를 질문으로 선택하는 게 유리함
            elif worst_case_size == min_worst_case_size:
                if potential_guess in self.candidates:
                     best_guess = potential_guess
                
        return best_guess
    
    '''
    추가해설: 난해한 함수이므로 예시를 통해 표현합니다.
    
    1. 현재 남음 정답 후보가 5개 [1234, 5678, 7890, 1357, 2468]이라 가정합니다.
    
    2. 각 후보와 5040개의 모든 조합과 비교해가며 (x S y B) 조합의 개수를 찾아냅니다. 예를 들어 정답 후보의 결과는 (1,2): 2개, (0,2): 3개, (1,1): 5개 입니다.
    
    3. 정답 후보 1234의 최악의 시나리오는 (1,1): 5 이므로 worst_case_size는 5입니다.
    
    4. 2-3 과정을 반복하여 나머지 정답 후보의 worst_case_size를 구해봅니다. (예: 5678: 6, 7890: 11, 2468: 4)
    
    5. 5개의 정답 후보중 worst_case_size가 가장 작은 수는 2468: 4개 이므로, 2468이 best_guess가 됩니다. 즉, 2468이 다음 질문에 대한 최고의 추측이 됩니다.
    '''

    def validate_answer(self, answer: str) -> bool:
        """
        입력된 정답이 게임 설정에 맞는지 검사합니다.
        문제가 있으면 에러 메시지를 출력하고 False를 반환합니다.
        """
        # 검사 1: 숫자 여부 검사
        if not answer.isdigit():
            return False, f"입력 오류: 숫자만 입력해야 합니다. (입력값: '{answer}')"
        
        # 검사 2: 자릿수 확인
        if len(answer) != self.scale:
            return False, f"자릿수 불일치! 설정은 {self.scale}자리인데, 입력은 {len(answer)}자리입니다."
        
        # 검사 3: 중복 숫자 검사
        if len(set(answer)) != len(answer):
            return False, f"규칙 오류: 중복된 숫자가 있습니다. (입력값: '{answer}')"
        
        # 모든 검사 통과
        return True, ""
    
    def play_game(self, secret_answer: str, stop_callback=None):
        """
        컴퓨터가 `find_next_best_guess`를 호출하며 게임을 진행합니다.
        """
        
        # [수정] 튜플 언패킹 (성공여부, 에러메시지)
        is_valid, err_msg = self.validate_answer(secret_answer)
        
        # 유효하지 않은 입력(False)이라면 에러 메시지를 yield 하고 종료
        if not is_valid:
            yield f"⛔ {err_msg}"
            return
        else:
            # 무거운 연산 시작 전에 메시지를 먼저 던져야 화면이 안 멈춥니다!
            yield "🎲 게임 데이터를 생성하고 있습니다... (잠시만 기다려주세요)"
            
            # [체크 1] 무거운 연산 전 체크
            if stop_callback and stop_callback(): return
            
            self.generate_all_candidates() # (10)P(n)개로 시작
            guess_count = 0        
            
            while True:
                
                # [체크 2] 매 턴마다 중단 여부 확인!
                # 사용자가 홈 버튼을 눌러서 page가 바뀌었다면 여기서 루프를 탈출함
                if stop_callback and stop_callback():
                    break
                try:
                    guess_count += 1
                    
                    lines = []
                    
                    lines.append(f"--- {guess_count}회차 추측 ---")
                    lines.append(f"계산 시작... (현재 후보: {len(self.candidates)}개)")
                    
                    
                        
            
                    # 1. 효율성을 위해 하드코딩
                    if guess_count == 1:
                        # 첫 추측은 5040개 전체에 대해 계산해야 하므로 매우 오래 걸립니다. (수 분 소요 가능)
                        # 검증된 최적의 첫 추측인 "0123" 또는 '1234'를 하드코딩하여 시간을 절약합니다.
                        current_guess = self.DIGITS[:self.scale]
                    
                    # 하드코딩 대신, AI가 다음 추측을 계산
                    else:
                        current_guess = self.find_next_best_guess(stop_callback = stop_callback)
                    
                    lines.append(f"컴퓨터의 추측: {current_guess}")
            
                    # 2. 실제 S/B 결과 확인
                    s, b = self.check_sb(current_guess, secret_answer)
                    lines.append(f"결과: {s}S {b}B")
                    
                    # 모아둔 줄들을 줄바꿈(\n)으로 연결해서 한 덩어리로 보냅니다.
                    full_message = "\n\n".join(lines) 
                    yield full_message
                    
                    # 3. 정답 확인
                    if s == self.scale:
                        yield(f"정답! {guess_count}회 만에 맞혔습니다.")
                        break
                        
                    if guess_count > 10: # 안전장치
                         print("AI가 10회 안에 맞히지 못했습니다.")
                         break
            
                    # 4. 후보 리스트 필터링
                    self.candidates = self.filter_candidates(current_guess, s, b)
                    
                    if not self.candidates:
                        yield("오류: 후보 리스트가 비었습니다. (모순 발생)")
                        break
                except InterruptedError:
                    # 내부에서 중단 에러가 발생하면 여기서 catch하고 종료
                    yield "⛔ 사용자 요청으로 연산을 중단했습니다."
                    break

#game = NumberBaseballGame(n = 5)
#game.play_game('37209')