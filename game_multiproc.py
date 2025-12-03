import itertools
import collections
import time
import concurrent.futures


# [추가] 별도 프로세스에서 실행될 "무거운" 연산 함수
# 이 함수는 클래스 밖(전역 스코프)에 있어야 프로세스 간 전달(Pickling)이 원활합니다.
def _worker_calculate_guess(candidates, all_possible_numbers):
    """
    실제 미니맥스 알고리즘을 수행하는 워커 함수입니다.
    메인 프로세스와 메모리를 공유하지 않으므로 필요한 데이터(후보군 리스트 등)를 인자로 모두 받아야 합니다.
    """
    # 최적화: 남은 후보가 2개 이하면 계산 불필요
    if len(candidates) <= 2:
        return candidates[0]

    min_worst_case_size = float('inf')
    best_guess = ""
    
    # 5자리일 경우 all_possible_numbers는 약 3만 개, candidates는 줄어듦.
    # 이중 루프 연산 (3만 x N)
    for potential_guess in all_possible_numbers:
        partitions = collections.defaultdict(int)
        
        for candidate in candidates:
            # check_sb 로직을 내장 (함수 호출 오버헤드 줄이기 위해 인라인 권장하지만, 
            # 여기서는 편의상 NumberBaseballGame.check_sb 정적 메서드 로직을 풀어씀)
            
            # --- [check_sb 로직 인라인 시작] ---
            strikes = 0
            for g, a in zip(potential_guess, candidate):
                if g == a:
                    strikes += 1
            common_digits = len(set(potential_guess) & set(candidate))
            balls = common_digits - strikes
            # --- [check_sb 로직 인라인 끝] ---
            
            partitions[(strikes, balls)] += 1
        
        if not partitions:
            continue
            
        worst_case_size = max(partitions.values())
        
        if worst_case_size < min_worst_case_size:
            min_worst_case_size = worst_case_size
            best_guess = potential_guess
        
        elif worst_case_size == min_worst_case_size:
            if potential_guess in candidates:
                best_guess = potential_guess
                
    return best_guess


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
    
    
    # [수정됨] 멀티프로세싱을 적용한 find_next_best_guess
    def find_next_best_guess(self, stop_callback=None) -> str:
        """
        멀티프로세싱을 사용하여 다음 추측을 계산합니다.
        """
        # 1. 후보가 매우 적을 때는 굳이 프로세스를 띄울 필요 없음 (오버헤드 방지)
        if len(self.candidates) <= 2:
            return self.candidates[0]

        # 2. ProcessPoolExecutor를 사용하여 별도 프로세스에서 연산 수행
        # max_workers=1로 설정하여 무거운 연산을 담당할 1개의 전용 코어를 할당
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            
            # 주의: stop_callback은 피클링이 불가능하므로 워커에 전달하지 않습니다.
            # 워커는 계산만 담당하고, 중단 요청은 메인 스레드에서 결과 대기 중에 처리합니다.
            
            # 워커에 작업 제출 (self.candidates와 self.all_possible_numbers를 복사해서 넘김)
            future = executor.submit(_worker_calculate_guess, self.candidates, self.all_possible_numbers)
            
            # [수정된 부분] 무작정 기다리지 않고, 0.1초마다 중단 여부를 체크합니다.
            while not future.done():
                
                # 1. 메인 UI에서 중단 요청이 있었는지 확인
                if stop_callback and stop_callback():
                    # 중단 요청이 오면, 더 이상 기다리지 않고 강제 종료
                    # (주의: 워커 프로세스는 하던 일을 마칠 때까지 백그라운드에서 조금 더 돌 수 있습니다)
                    executor.shutdown(wait=False, cancel_futures=True) 
                    raise InterruptedError("Game Stopped by User")
                
                # 2. 중단 요청이 없다면 잠시 대기 (CPU 양보)
                time.sleep(0.05)
            
            # 루프를 탈출했다면 작업이 완료된 것임
            return future.result()

    
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