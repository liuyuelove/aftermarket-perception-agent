import cv2

class cv_video_proc():
    '''
    video process using opencv
    '''
    def __init__(self):
        self.video_is_open = False
        self.video_is_create = False
    
    def video_open(self, video_path_i, video_target_fps_i=None):
        '''
        打开video
        param:
            video_path_i: video路径, str
        return:
            True or False
        '''
        if self.video_is_open:
            self.video_close()
            self.video_is_open = False
        
        self.video_cap = cv2.VideoCapture(video_path_i)
        if not self.video_cap.isOpened():
            print(f"Error: Could not open video {video_path_i}.")
            return False
        
        self.video_path = video_path_i
        self.video_is_open = True
        self.frame_id = 0
        self.video_src_frame_num = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_src_fps = self.video_cap.get(cv2.CAP_PROP_FPS)
        self.video_src_width = self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.video_src_height = self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        self.video_target_fps = self.video_src_fps
        self.video_target_frame_num = self.video_src_frame_num
        self.frame_extract_step = 1
        self.frame_extract_next_id = 0
        if video_target_fps_i != None:
            self.set_video_target_fps(video_target_fps_i)
        return True
    
    def set_video_target_fps(self, target_fps_i):
        '''
        设置video帧率, 若目标帧率小于实际帧率, 将通过抽帧的方式实现目标帧率, 否则使用实际帧率
        param:
            target_fps_i: 目标帧率
        return:
            True or False
        '''
        if self.video_is_open:
            if target_fps_i <= self.video_src_fps:
                self.video_target_fps = target_fps_i
                self.frame_extract_step = self.video_src_fps / target_fps_i
                self.video_target_frame_num = int(self.video_src_frame_num / self.frame_extract_step)
                return True
        return False
    
    def get_frames(self, get_frame_num_i=None):
        '''
        获取指定帧数图像, 图像为经过按照 self.video_target_fps 抽帧后的图像
        param:
            get_frame_num_i: 要获取的帧数, 若为None, 将获取所有帧
        return:
            若获取成功, 返回[frame_id], [frame], 若获取失败, 返回[], []
        '''
        if self.video_is_open == False:
            raise 'Please open video first!'

        if get_frame_num_i == None:
            get_frame_num = self.video_target_frame_num
        else:
            get_frame_num = get_frame_num_i
        
        frame_id = []
        frame_data = []
        for _ in range(get_frame_num):
            while self.frame_id <= int(self.frame_extract_next_id):
                ret, frame = self.video_cap.read()
                if not ret:
                    self.video_close()
                    return [], []
                self.frame_id += 1

            self.frame_extract_next_id += self.frame_extract_step
            frame_id.append(self.frame_id-1)
            frame_data.append(frame)
        return frame_id, frame_data
    
    def video_close(self):
        '''
        关闭video
        '''
        if self.video_is_open:
            self.video_cap.release()
            self.video_is_open = False
        return
    
    def video_create(self, video_path_i, video_fps_i=25, video_width_i=1280, video_height_i=720, is_color_i=True):
        '''
        创建video
        param:
            video_path_i: video路径, str
            video_fps_i: video帧率, int
            video_width_i: video宽度, int
            video_height_i: video高度, int
        return:
            True or False
        '''
        if self.video_is_create:
            self.video_create_done()
            self.video_is_create = False
            
        video_suffix = str(video_path_i).split('.')[-1]
        if video_suffix == 'avi':
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
        elif video_suffix == 'mp4':
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        else:
            raise 'video_suffix error!'
        
        self.video_wr = cv2.VideoWriter(video_path_i, fourcc, video_fps_i, (video_width_i, video_height_i), isColor=is_color_i)
        
        self.video_is_create = True
        return True
    
    def video_create_done(self):
        '''
        完成创建video
        '''
        if self.video_is_create:
            self.video_wr.release()
            self.video_is_create = False
        return
    
    def video_write(self, frame_data_i):
        '''
        写入序列图像
        param:
            frame_data_i: 要写入的图像数据, frame or [frame0, frame1, ...]
        return:
            True or False
        '''
        
        if self.video_is_create == False:
            raise 'Please create video first!'
        
        if isinstance(frame_data_i, list) == False:
            frame_data_list = [frame_data_i]
        else:
            frame_data_list = frame_data_i
        
        for frame in frame_data_list:
            self.video_wr.write(frame)
        return True
    