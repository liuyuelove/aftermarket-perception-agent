# moviepy > 2.0.0
# from moviepy.video.io.VideoFileClip import VideoFileClip

# moviepy 1.x
from moviepy.editor import VideoFileClip, concatenate_videoclips
from typing import List


def video_merge(video_list_i: List[VideoFileClip]) -> VideoFileClip:
    return concatenate_videoclips(video_list_i)

def write_video_to_file(video_obj_i: VideoFileClip, video_file_path_i: str, fps_i=None, codec_i=None, bitrate_i=None, audio_i=False, logger_i='bar'):
    video_obj_i.write_videofile(video_file_path_i, fps=fps_i, codec=codec_i, bitrate=bitrate_i, audio=audio_i, logger=logger_i)

def video_files_merge(src_video_path_i: List[str], dst_video_path_i: str, fps_i=None, codec_i=None, bitrate_i=None):
    print(f'start merge video: {src_video_path_i}')
    video_obj_list = []
    for video_path in src_video_path_i:
        video_obj_list.append(VideoFileClip(video_path))
    
    merged_video = video_merge(video_obj_list)
    write_video_to_file(merged_video, dst_video_path_i, fps_i=fps_i, codec_i=codec_i, bitrate_i=bitrate_i)
    
    for video in video_obj_list:
        video.close()
    merged_video.close()
    print('merge finish.')


class mp_video_proc():
    '''
    video process using moviepy
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
        
        self.video_cap = VideoFileClip(video_path_i)

        self.video_path = video_path_i
        self.video_is_open = True
        self.frame_id = 0
        self.video_src_duration = self.video_cap.duration # 视频时长, 秒
        self.video_src_frame_num = self.video_cap.reader.nframes
        self.video_src_fps = self.video_cap.reader.fps
        self.video_src_width, self.video_src_height = self.video_cap.size
        
        self.video_target_fps = self.video_src_fps
        self.video_target_frame_num = self.video_src_frame_num
        self.frame_extract_step = 1
        self.frame_extract_next_id = 0
        if video_target_fps_i != None:
            self.set_video_target_fps(video_target_fps_i)
        self.sub_clip = []
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
            
            extract_frame_time = self.frame_extract_next_id / self.video_src_fps
            if extract_frame_time > self.video_src_duration:
                break
            
            frame = self.video_cap.get_frame(extract_frame_time)
            
            frame_id.append(self.frame_extract_next_id)
            frame_data.append(frame)
            
            self.frame_extract_next_id += self.frame_extract_step
        return frame_id, frame_data
    
    def video_close(self):
        '''
        关闭video
        '''
        if self.video_is_open:
            self.video_cap.close()
            if self.sub_clip is not []:
                for subclip in self.sub_clip:
                    subclip.close()
            self.video_is_open = False
        return
    
    def video_clip(self, clip_time_s_i=[(0, 5)], without_audio_i=True):
        '''
        clip video into several clips
        param:
            clip_time_s_i: [(clip_start_time_i, clip_end_time_i), ...], second
        return:
            [video_clip1, video_clip2...]
        '''
        
        for clip_start_time, clip_end_time in clip_time_s_i:
            # 裁剪视频
            if without_audio_i:
                subclip = self.video_cap.subclip(clip_start_time, clip_end_time).without_audio()
            else:
                subclip = self.video_cap.subclip(clip_start_time, clip_end_time)
            # 保存裁剪后的视频
            self.sub_clip.append(subclip)

        return self.sub_clip
    