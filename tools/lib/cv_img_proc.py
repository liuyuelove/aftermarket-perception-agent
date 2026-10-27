import cv2
import numpy as np


def write_ndarray_to_img(img_path_i, img_data_i):
    cv2.imwrite(img_path_i, img_data_i)


def read_img_to_ndarray(img_path_i, flags_i=cv2.IMREAD_COLOR):
    img_data = cv2.imread(str(img_path_i), flags_i)
    return img_data


def write_ndarray_to_bin(img_path_i, img_data_i):
    with open(img_path_i, 'wb') as f_oj:
        img_data_i.tofile(f_oj)


def read_bin_to_ndarray(img_path_i, dtype_i=np.uint8):
    with open(img_path_i, 'rb') as f_oj:
        img_data = np.fromfile(f_oj, dtype_i)
    return img_data


def img_cvt_color(img_data_i, src_color_i='BGR', dst_color_i='GRAY'):
    code = getattr(cv2, f'COLOR_{src_color_i.upper()}2{dst_color_i.upper()}')
    return cv2.cvtColor(img_data_i, code)


def img_crop_with_expand(org_img_i, crop_param_i, expand_size_i=(0, 0), with_param_out_i=False):
    """
    Crop the image with expand.

    Args:
        org_img_i: ndarray, [H,W,C]
        crop_param_i: (x0, y0, crop_w, crop_h)
        expand_size_i: (x, y), left and right each expand x/2, up and down each expand y/2
        with_param_out_i: bool, if True, return the crop parameter
    Returns:
        cropped_img: ndarray, [H,W,C]
        crop_param: (x0, y0, crop_w, crop_h), the cropped image parameter
    """
    h, w = org_img_i.shape[:2]

    crop_x0, crop_y0, crop_w, crop_h = crop_param_i
    crop_x0 = int(float(crop_x0) - expand_size_i[0] / 2)
    crop_y0 = int(float(crop_y0) - expand_size_i[1] / 2)
    crop_x1 = int(float(crop_x0) + float(crop_w - 1) + expand_size_i[0] / 2)
    crop_y1 = int(float(crop_y0) + float(crop_h - 1) + expand_size_i[1] / 2)

    if crop_x0 < 0:
        crop_x0 = 0
    if crop_y0 < 0:
        crop_y0 = 0
    if crop_x1 >= w:
        crop_x1 = w - 1
    if crop_y1 >= h:
        crop_y1 = h - 1

    # 执行裁剪操作
    cropped_img = org_img_i[crop_y0:crop_y1+1, crop_x0:crop_x1+1]

    if with_param_out_i:
        return cropped_img, (crop_x0, crop_y0, crop_x1-crop_x0+1, crop_y1-crop_y0+1)
    else:
        return cropped_img

def img_resize(img_data_i, resize_resolution_i, with_param_out_i=False):
    """
    Resize the image.

    Args:
        img_data_i: ndarray, [H,W,C]
        resize_resolution_i: [w, h]
        with_param_out_i: bool, if True, return the resize coefficient
    Returns:
        resized_img: ndarray, [H,W,C]
        resize_coeff: (resize_coeff_x, resize_coeff_y), the resize coefficient
    """
    resized_img = cv2.resize(img_data_i, resize_resolution_i, interpolation=cv2.INTER_LINEAR)
    if with_param_out_i:
        resize_coeff_x = resize_resolution_i[0] / img_data_i.shape[1]
        resize_coeff_y = resize_resolution_i[1] / img_data_i.shape[0]
        return resized_img, (resize_coeff_x, resize_coeff_y)
    else:
        return resized_img

def img_flip(img_data_i, flip_mode_i = 1):
    """
    Flip the image.

    Args:
        img_data_i: ndarray, [H,W,C]
        flip_mode_i: int, 0(up down flip), 1(left right flip), -1(both up down and left right flip)
    Returns:
        flipped_img: ndarray, [H,W,C]
    """
    return cv2.flip(img_data_i, flip_mode_i)

def img_show(img_data_i, win_name_i='window', wait_key_i=0):
    cv2.imshow(win_name_i, img_data_i)
    cv2.waitKey(wait_key_i)

def img_add_line(img_i, pt1_i, pt2_i, color_i=(0, 0, 255), thickness_i=1):
    '''
    Add line to image.

    Args:
        img_i: ndarray, [H,W,C]
        pt1_i: line start point, int, (x, y)
        pt2_i: line end point, int, (x, y)
        color_i: (B, G, R)
        thickness_i: int, line thickness
    Returns: ndarray, [H,W,C]
    '''
    return cv2.line(img_i, pt1_i, pt2_i, color_i, thickness_i)

def img_add_circle(img_i, center_i, radius_i=1, color_i=(0, 0, 255), thickness_i=1):
    '''
    Add circle to image.

    Args:
        img_i: ndarray, [H,W,C]
        center_i: circle center, int, (x, y)
        radius_i: int, circle radius
        color_i: (B, G, R)
        thickness_i: int, circle thickness
    Returns: ndarray, [H,W,C]
    '''
    return cv2.circle(img_i, center_i, radius_i, color_i, thickness_i)

def img_add_text(img_i, text_i, position_i, font_i=cv2.FONT_HERSHEY_SIMPLEX, font_scale_i=1.0, color_i=(255, 255, 255), thickness_i=2, line_type_i=cv2.LINE_AA):
    '''
    Add text to image.

    Args:
        img_i: ndarray, [H,W,C]
        text_i: str, text to be added
        position_i: text start position, int, (x, y)
        font_i: font type
        font_scale_i: font scale
        color_i: (B, G, R)
        thickness_i: int, text thickness
        line_type_i: line type
    Returns: ndarray, [H,W,C]
    '''
    return cv2.putText(img_i, text_i, position_i, font_i, font_scale_i, color_i, thickness_i, line_type_i)

def img_draw_rectangle(img_i, top_left_i, bottom_right_i, color_i=(0, 0, 255), thickness_i=2):
    '''
    Draw rectangle on image.

    Args:
        img_i: ndarray, [H,W,C]
        top_left_i: rectangle top left point, int, (x, y)
        bottom_right_i: rectangle bottom right point, int, (x, y)
        color_i: (B, G, R)
        thickness_i: int, rectangle thickness
    Returns: ndarray, [H,W,C]
    '''
    return cv2.rectangle(img_i, top_left_i, bottom_right_i, color_i, thickness_i)

# warper: Warper
class Warper(object):
    
    def __init__(self, src=None, dst=None, img_size=(256, 256)):
        '''
        Initialize warper.

        Args:
            src: source points, np.float32, (4, 2)
            dst: destination points, np.float32, (4, 2)
            img_size: image size, (w, h)
        '''
        self.set_perspective_transform(src, dst, img_size)
    
    def set_perspective_transform(self, src=None, dst=None, img_size=(256, 256)):
        '''
        Set perspective transform.

        Args:
            src: source points, np.float32, (4, 2)
            dst: destination points, np.float32, (4, 2)
            img_size: image size, (w, h)
        '''
        if src is None or dst is None:
            self.src = np.float32(img_size * np.float32(
                [[247, 231], [381, 231],
                 [37, 350], [497, 350]]) / [256, 256])
            self.dst = np.float32(img_size * np.float32(
                [[220, 200], [420, 200],
                 [220, 359], [420, 359]]) / [128, 64]
            )
        else:
            self.src = np.float32(src)
            self.dst = np.float32(dst)
        self.M = cv2.getPerspectiveTransform(self.src, self.dst)
        self.M_inv = cv2.getPerspectiveTransform(self.dst, self.src)
        return self.M, self.M_inv
    
    def warp_img(self, img, target_shape=(128, 64), border_mode='BORDER_CONSTANT', border_value=(0, 0, 0)):
        '''
        Warp image.

        Args:
            img: image to be warped, ndarray, [H,W,C]
            target_shape: target image shape, (w, h)
            border_mode: border mode
            border_value: border value
        Returns: ndarray, [H,W,C]
        '''
        border_mode = getattr(cv2, border_mode.upper())
        return cv2.warpPerspective(img.astype(np.float32), self.M, target_shape, borderMode=border_mode, borderValue=border_value)
    
    def unwarp_img(self, img, target_shape=(128, 64), border_mode='BORDER_CONSTANT', border_value=(0, 0, 0)):
        '''
        Unwarp image.

        Args:
            img: image to be unwarped, ndarray, [H,W,C]
            target_shape: target image shape, (w, h)
            border_mode: border mode
            border_value: border value
        Returns: ndarray, [H,W,C]
        '''
        border_mode = getattr(cv2, border_mode.upper())
        return cv2.warpPerspective(img.astype(np.float32), self.M_inv, target_shape, borderMode=border_mode, borderValue=border_value)

    def warp_points(self, points):
        '''
        Warp points.

        Args:
            points: points to be warped, np.float32, (N, 2)
        Returns: np.float32, (N, 2)
        '''
        points_tran = []
        for point in points:
            coord = np.append(point, 1)
            trans = np.dot(self.M, coord)
            point_tran = (trans[:2] / trans[2]).astype(np.int32)
            points_tran.append(point_tran)
        return np.array(points_tran)
    
    def unwarp_points(self, points):
        '''
        Unwarp points.

        Args:
            points: points to be unwarped, np.float32, (N, 2)
        Returns: np.float32, (N, 2)
        '''
        points_tran = []
        for point in points:
            coord = np.append(point, 1)
            trans = np.dot(self.M_inv, coord)
            point_tran = (trans[:2] / trans[2]).astype(np.int32)
            points_tran.append(point_tran)
        return np.array(points_tran)

def img_rotate(img_data_i, angle_i=0, scale_i=1.0, auto_resolution_i=False):
    '''
    Rotate image.

    Args:
        img_data_i: ndarray, [H,W,C]
        angle_i: float, degree, 逆时针旋转角度, 负值表示顺时针旋转
        scale_i: float, 缩放比例
        auto_resolution_i: bool, 是否自动计算旋转后的图像尺寸, False表示使用原图像尺寸
    Returns: ndarray, [H,W,C]
    '''
    
    height, width = img_data_i.shape[:2]
    center = (width/2, height/2)
    
    rotate_mat = cv2.getRotationMatrix2D(center, angle_i, scale_i)

    if auto_resolution_i:
        # 计算旋转后的图像尺寸
        cos = np.abs(rotate_mat[0, 0])
        sin = np.abs(rotate_mat[0, 1])

        new_width = int((height * sin) + (width * cos))
        new_height = int((height * cos) + (width * sin))

        # 调整旋转矩阵的平移部分，使图像居中
        rotate_mat[0, 2] += (new_width / 2) - center[0]
        rotate_mat[1, 2] += (new_height / 2) - center[1]

        width = new_width
        height = new_height
    
    rotate_img = cv2.warpAffine(img_data_i, rotate_mat, (width, height))
    return rotate_img

    
