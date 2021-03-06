# -*-coding: utf-8 -*-
"""
    @Project: VOCtrainval_06-Nov-2007
    @File   : net_batch_norm.py
    @Author : panjq
    @E-mail : pan_jinquan@163.com
    @Date   : 2018-11-20 21:03:42
"""

import numpy as np
import tensorflow as tf
import os
from datetime import datetime
from utils.create_tf_record import *

labels_nums = 5  # 类别个数
batch_size = 16  #
resize_height = 224  # 指定存储图片高度
resize_width = 224  # 指定存储图片宽度
depths = 3
data_shape = [batch_size, resize_height, resize_width, depths]

# 定义input_images为图片数据
input_images = tf.placeholder(dtype=tf.float32, shape=[None, resize_height, resize_width, depths], name='input')
# 定义input_labels为labels数据
input_labels = tf.placeholder(dtype=tf.int32, shape=[None], name='label')
# input_labels = tf.placeholder(dtype=tf.int32, shape=[None, labels_nums], name='label')

# 定义dropout的概率
keep_prob = tf.placeholder(tf.float32,name='keep_prob')
is_training = tf.placeholder(tf.bool, name='is_training')


def net_batch_norm(inputs, labels_nums, keep_prob, is_training):
    # 卷积层1
    conv_2d_w1 = tf.Variable(tf.truncated_normal([5, 5, 3, 32], stddev=0.0001))
    conv_2d_b1 = tf.Variable(tf.truncated_normal([32]))
    conv2d_1 = tf.nn.conv2d(inputs, conv_2d_w1, strides=[1, 1, 1, 1], padding='SAME') + conv_2d_b1
    conv2d_1 = tf.contrib.layers.batch_norm(conv2d_1, decay=0.96, is_training=is_training)
    conv2d_1_output = tf.nn.relu(conv2d_1)
    pool_1 = tf.nn.max_pool(conv2d_1_output,
                            ksize=[1, 3, 3, 1],
                            strides=[1, 2, 2, 1],
                            padding='SAME')
    # 卷积层2
    conv_2d_w2 = tf.Variable(tf.truncated_normal([5, 5, 32, 32], stddev=0.001))
    conv_2d_b2 = tf.Variable(tf.truncated_normal([32]))
    conv2d_2 = tf.nn.conv2d(pool_1, conv_2d_w2, strides=[1, 1, 1, 1], padding='SAME') + conv_2d_b2
    conv2d_2 = tf.contrib.layers.batch_norm(conv2d_2, decay=0.96, is_training=is_training)
    conv2d_2_output = tf.nn.relu(conv2d_2)

    pool_2 = tf.nn.max_pool(conv2d_2_output,
                            ksize=[1, 3, 3, 1],
                            strides=[1, 2, 2, 1],
                            padding='SAME')
    # 卷积层3
    conv_2d_w3 = tf.Variable(tf.truncated_normal([5, 5, 32, 64], stddev=0.01))
    conv_2d_b3 = tf.Variable(tf.truncated_normal([64]))
    conv2d_3 = tf.nn.conv2d(pool_2, conv_2d_w3, strides=[1, 1, 1, 1], padding='SAME') + conv_2d_b3
    conv2d_3 = tf.contrib.layers.batch_norm(conv2d_3, decay=0.96, is_training=is_training)
    conv2d_3_output = tf.nn.relu(conv2d_3)
    pool_3 = tf.nn.max_pool(conv2d_3_output,
                            ksize=[1, 3, 3, 1],
                            strides=[1, 2, 2, 1],
                            padding='SAME')
    # 卷积层接全连接层需要确定输入的维度
    # pool3_flat = tf.reshape(pool_3, [-1, 4 * 4 * 64])
    pool3_flat = tf.contrib.layers.flatten(inputs=pool_3)

    pool3_flat_shape=pool3_flat.get_shape().as_list()
    fc_dim=pool3_flat_shape[1]
    # 全连接层1
    fc_w1 = tf.Variable(tf.truncated_normal([fc_dim, 1024], stddev=0.1))
    fc_b1 = tf.Variable(tf.truncated_normal([1024]))
    fc_1 = tf.matmul(pool3_flat, fc_w1) + fc_b1
    fc_1 = tf.contrib.layers.batch_norm(fc_1, decay=0.96, is_training=is_training)
    fc_1_output = tf.nn.relu(fc_1)

    # 全连接层2
    fc_w2 = tf.Variable(tf.truncated_normal([1024, 128], stddev=0.1))
    fc_b2 = tf.Variable(tf.truncated_normal([128]))
    fc_2 = tf.matmul(fc_1_output, fc_w2) + fc_b2
    fc_2 = tf.contrib.layers.batch_norm(fc_2, decay=0.96, is_training=is_training)
    fc_2_output = tf.nn.relu(fc_2)

    fc2_drop = tf.nn.dropout(fc_2_output, keep_prob)

    # 输出层（也是全连接层）
    out_w1 = tf.Variable(tf.truncated_normal([128, labels_nums]))
    out_b1 = tf.Variable(tf.truncated_normal([labels_nums]))
    combine = tf.matmul(fc2_drop, out_w1) + out_b1
    return combine

def net_evaluation(sess,loss,accuracy,val_images_batch,val_labels_batch,val_nums):
    val_max_steps = int(val_nums / batch_size)
    val_losses = []
    val_accs = []
    for _ in range(val_max_steps):
        val_x, val_y = sess.run([val_images_batch, val_labels_batch])
        # print('labels:',val_y)
        # val_loss = sess.run(loss, feed_dict={x: val_x, y: val_y, keep_prob: 1.0})
        # val_acc = sess.run(accuracy,feed_dict={x: val_x, y: val_y, keep_prob: 1.0})
        val_loss,val_acc = sess.run([loss,accuracy], feed_dict={input_images: val_x, input_labels: val_y, keep_prob:1.0, is_training: False})
        val_losses.append(val_loss)
        val_accs.append(val_acc)
    mean_loss = np.array(val_losses, dtype=np.float32).mean()
    mean_acc = np.array(val_accs, dtype=np.float32).mean()
    return mean_loss, mean_acc

def step_train(train_op,loss,accuracy,
               train_images_batch,train_labels_batch,train_nums,train_log_step,
               val_images_batch,val_labels_batch,val_nums,val_log_step,
               snapshot_prefix,snapshot):
    '''
    循环迭代训练过程
    :param train_op: 训练op
    :param loss:     loss函数
    :param accuracy: 准确率函数
    :param train_images_batch: 训练images数据
    :param train_labels_batch: 训练labels数据
    :param train_nums:         总训练数据
    :param train_log_step:   训练log显示间隔
    :param val_images_batch: 验证images数据
    :param val_labels_batch: 验证labels数据
    :param val_nums:         总验证数据
    :param val_log_step:     验证log显示间隔
    :param snapshot_prefix: 模型保存的路径
    :param snapshot:        模型保存间隔
    :return: None
    '''
    saver = tf.train.Saver()
    max_acc = 0.0
    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        sess.run(tf.local_variables_initializer())
        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)
        for i in range(max_steps + 1):
            batch_input_images, batch_input_labels = sess.run([train_images_batch, train_labels_batch])
            _, train_loss = sess.run([train_op, loss], feed_dict={input_images: batch_input_images,
                                                                  input_labels: batch_input_labels,
                                                                  keep_prob: 0.5, is_training: True})
            # train测试(这里仅测试训练集的一个batch)
            if i % train_log_step == 0:
                train_acc = sess.run(accuracy, feed_dict={input_images: batch_input_images,
                                                          input_labels: batch_input_labels,
                                                          keep_prob: 1.0, is_training: False})
                print("%s: Step [%d]  train Loss : %f, training accuracy :  %g" % (
                datetime.now(), i, train_loss, train_acc))

            # val测试(测试全部val数据)
            if i % val_log_step == 0:
                mean_loss, mean_acc = net_evaluation(sess, loss, accuracy, val_images_batch, val_labels_batch, val_nums)
                print("%s: Step [%d]  val Loss : %f, val accuracy :  %g" % (datetime.now(), i, mean_loss, mean_acc))

            # 模型保存:每迭代snapshot次或者最后一次保存模型
            if (i % snapshot == 0 and i > 0) or i == max_steps:
                print('-----save:{}-{}'.format(snapshot_prefix, i))
                saver.save(sess, snapshot_prefix, global_step=i)
            # 保存val准确率最高的模型
            if mean_acc > max_acc and mean_acc > 0.7:
                max_acc = mean_acc
                path = os.path.dirname(snapshot_prefix)
                best_models = os.path.join(path, 'best_models_{}_{:.4f}.ckpt'.format(i, max_acc))
                print('------save:{}'.format(best_models))
                saver.save(sess, best_models)

        coord.request_stop()
        coord.join(threads)

def train(train_record_file,
          train_log_step,
          train_param,
          val_record_file,
          val_log_step,
          labels_nums,
          data_shape,
          snapshot,
          snapshot_prefix):
    '''
    :param train_record_file: 训练的tfrecord文件
    :param train_log_step: 显示训练过程log信息间隔
    :param train_param: train参数
    :param val_record_file: 验证的tfrecord文件
    :param val_log_step: 显示验证过程log信息间隔
    :param val_param: val参数
    :param labels_nums: labels数
    :param data_shape: 输入数据shape
    :param snapshot: 保存模型间隔
    :param snapshot_prefix: 保存模型文件的前缀名
    :return:
    '''
    [base_lr,max_steps]=train_param
    [batch_size,resize_height,resize_width,depths]=data_shape

    # 获得训练和测试的样本数
    train_nums=get_example_nums(train_record_file)
    val_nums=get_example_nums(val_record_file)
    print('train nums:%d,val nums:%d'%(train_nums,val_nums))

    # 从record中读取图片和labels数据
    # train数据,训练数据一般要求打乱顺序shuffle=True
    train_images, train_labels = read_records(train_record_file, resize_height, resize_width, type='normalization')
    train_images_batch, train_labels_batch = get_batch_images(train_images, train_labels,
                                                              batch_size=batch_size, labels_nums=labels_nums,
                                                              one_hot=False, shuffle=True)
    # val数据,验证数据可以不需要打乱数据
    val_images, val_labels = read_records(val_record_file, resize_height, resize_width, type='normalization')
    val_images_batch, val_labels_batch = get_batch_images(val_images, val_labels,
                                                          batch_size=batch_size, labels_nums=labels_nums,
                                                          one_hot=False, shuffle=False)

    reg = tf.contrib.layers.l2_regularizer(scale=0.1)

    combine = net_batch_norm(inputs=input_images,
                             labels_nums=labels_nums,
                             keep_prob=keep_prob,
                             is_training=is_training)

    pred = tf.cast(tf.argmax(tf.nn.softmax(combine), 1), tf.int32)
    weights = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)
    reg_ws = tf.contrib.layers.apply_regularization(reg, weights_list=weights)
    # reg_ws = tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)
    update_avg = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    loss = tf.reduce_sum(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=input_labels, logits=combine))
    # loss = -tf.reduce_sum(y_*tf.log(tf.clip_by_value(pred,1e-11,1.0)))
    loss_fn = loss + tf.reduce_sum(reg_ws)
    with tf.control_dependencies(update_avg):
        train_op = tf.train.AdamOptimizer(base_lr).minimize(loss_fn)
    accuracy = tf.reduce_mean(tf.cast(tf.equal(pred, input_labels), tf.float32))

    saver = tf.train.Saver()
    sess = tf.Session()
    sess.run(tf.global_variables_initializer())
    # 循环迭代过程
    step_train(train_op, loss, accuracy,
               train_images_batch, train_labels_batch, train_nums, train_log_step,
               val_images_batch, val_labels_batch, val_nums, val_log_step,
               snapshot_prefix, snapshot)



if __name__ == '__main__':
    train_record_file='../dataset/dataset/record/train.tfrecords'
    val_record_file='../dataset/dataset/record/val.tfrecords'

    train_log_step=100
    base_lr = 0.001  # 学习率
    max_steps = 10000  # 迭代次数
    train_param=[base_lr,max_steps]

    val_log_step=200
    snapshot=2000#保存文件间隔
    snapshot_prefix='models/model.ckpt'
    train(train_record_file=train_record_file,
          train_log_step=train_log_step,
          train_param=train_param,
          val_record_file=val_record_file,
          val_log_step=val_log_step,
          labels_nums=labels_nums,
          data_shape=data_shape,
          snapshot=snapshot,
          snapshot_prefix=snapshot_prefix)


