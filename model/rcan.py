import tensorflow_addons as tfa
from tensorflow.python.keras.layers import Add, Multiply, Conv2D, Input, Lambda
from tensorflow.python.keras.models import Model

from model.common import normalize, denormalize, pixel_shuffle


def CALayer(x_in, num_filters, reduction=16): #x_in == num_filters
    x = tfa.layers.AdaptiveAveragePooling2D(1)(x_in)
    x = Conv2D(num_filters // reduction, 3, padding='same', activation='relu')(x)
    x = Conv2D(num_filters, 3, padding='same', activation='sigmoid')(x)
    x = Multiply()([x_in, x]) 
    return x

def RCAB(x_in, num_filters, reduction, scaling): #residual channel attention block
    x = Conv2D(num_filters, 3, padding='same', activation='relu')(x_in)
    x = Conv2D(num_filters, 3, padding='same')(x)
    x = CALayer(x, num_filters, reduction)
    
    if scaling:
        x = Lambda(lambda t: t * scaling)(x)
    x = Add()([x_in, x])
    return x
    
def resGroup(x_in, num_filters, num_res_blocks, reduction, scaling):
    for group in range(num_res_blocks):
        x = RCAB(x_in, num_filters, reduction, scaling)
    x = Conv2D(num_filters, 3, padding='same')(x)
    x = Add()([x_in, x])
    return x

def rcan(scale, num_filters=64, num_res_groups=10, num_res_blocks=20, reduction=16, scaling=1):
    x_in = Input(shape=(None, None, 3))
    x = Lambda(normalize)(x_in)

    x = b = Conv2D(num_filters, 3, padding='same')(x)
    for i in range(num_res_groups):
        b = resGroup(b, num_filters, num_res_blocks, reduction, scaling)
    b = Conv2D(num_filters, 3, padding='same')(b)
    x = Add()([x, b])
    
    x = upsample(x, scale, num_filters)
    x = Conv2D(3, 3, padding='same')(x)

    x = Lambda(denormalize)(x)
    return Model(x_in, x, name="rcan") 


def upsample(x, scale, num_filters):
    def upsample_1(x, factor, **kwargs):
        x = Conv2D(num_filters * (factor ** 2), 3, padding='same', **kwargs)(x)
        return Lambda(pixel_shuffle(scale=factor))(x)

    if scale == 2:
        x = upsample_1(x, 2, name='conv2d_1_scale_2')
    elif scale == 3:
        x = upsample_1(x, 3, name='conv2d_1_scale_3')
    elif scale == 4:
        x = upsample_1(x, 2, name='conv2d_1_scale_2')
        x = upsample_1(x, 2, name='conv2d_2_scale_2')

    return x
