#import numpy as np

class StateMachineV2:

    def __init__(self, 
                 n_states: int, #两个状态，驾驶员在位，不在位
                 state_durations: list, #切换到对应状态时最少保持的时间
                 state_time_threshes: list, # 报警触发所需要的持续时间
                 state_conf_threshes: list): # 报警的置信度，置信度总和必须大于1
        assert len(state_durations) == len(state_time_threshes) == len(state_conf_threshes) == n_states
        self.states = list(range(n_states))
        self.state_durations = state_durations
        self.state_time_threshes = state_time_threshes
        self.state_conf_threshes = state_conf_threshes

        # sequence of sequcence; vector of vector
        self.X = {state_i: [] for state_i in self.states}  # x sequence
        self.T = {state_i: [] for state_i in self.states}  # t sequence
        self.dT = {state_i: [] for state_i in self.states}  # delta_t sequence

        self.warn_sign = [False, ] * n_states
        self.weighted_states = [0, ] * n_states
        self.state_count = [0.0, ] * n_states

        self.cur_state = -1
        self.initialized = [False, ] * n_states

    def update(self, x, t_stamp):

        for state_i in self.states:
            self.X[state_i].append(x == state_i)
            self.T[state_i].append(t_stamp)
            self.dT[state_i].append(0)

            if len(self.X[state_i]) > 1:
                self.dT[state_i][-2] = self.T[state_i][-1] - self.T[state_i][-2]

                sum_state_i = 0
                for ind in range(len(self.dT[state_i])):
                    sum_state_i += self.dT[state_i][ind] * self.X[state_i][ind] 
                self.weighted_states[state_i] = sum_state_i / self.state_time_threshes[state_i]

                self.state_count[state_i] += self.dT[state_i][-2]
                if self.state_count[state_i] >= self.state_durations[state_i]:
                    self.warn_sign[state_i] = True
            else:
                self.weighted_states[state_i] = 0
                self.warn_sign[state_i] = True

            if not self.initialized[state_i]:
                self.initialized[state_i] = (t_stamp - self.T[state_i][0] > self.state_time_threshes[state_i])

            if self.cur_state != state_i and \
               self.initialized[state_i] and \
               self.warn_sign[state_i] and \
               self.X[state_i][0] == 1 and \
               (self.weighted_states[state_i] >= self.state_conf_threshes[state_i]):

                self.cur_state = state_i
                self.state_count[state_i] = 0
                self.warn_sign[state_i] = False

            if t_stamp - self.T[state_i][0] > self.state_time_threshes[state_i]:
                self.X[state_i].pop(0)
                self.T[state_i].pop(0)
                self.dT[state_i].pop(0)

            #print(f'initialized[{state_i}]: {self.initialized[state_i]}')
            #print(f'warn_sign[{state_i}]: {self.warn_sign[state_i]}')
            #print(f'weighted_states[{state_i}]: {self.weighted_states[state_i]}')
        #print(self.X)

        #print(self.cur_state)
        #print(f'---------t_stamp:{t_stamp}, x:{x}, cur_state:{self.cur_state}')
        #print([(xx, list(np.array(self.X[xx]).astype(int))) for xx in self.X])
