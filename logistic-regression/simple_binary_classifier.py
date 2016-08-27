# Simple binary linear classifier with synthetic data.
#
# Eli Bendersky (http://eli.thegreenplace.net)
# This code is in the public domain
from __future__ import print_function
import argparse
import matplotlib.pyplot as plt
import numpy as np
from timer import Timer
import sys

from regression_lib import *


def generate_data(k, num_neg_outliers=0):
    """Generates k data items with correct labels (+1 or -1) for each item.

    k: number of data points to generate.
    num_neg_outliers: number of outliers for the negative samples

    Returns X (k, 2) - k data items in 2D, and y (k, 1) - the correct label
    (+1 or -1) for each data item in X.
    """
    kneg, kpos = k / 2, k / 2
    kneg_regular = kneg - num_neg_outliers
    # Generate positive data items and negative data items; for negatives, the
    # "regulars" are generated using different parameters from "outliers".
    positives = (np.full((kpos, 2), 3.0) +
                 np.random.normal(scale=0.9, size=(kpos, 2)))
    outliers = (np.hstack((np.ones((num_neg_outliers, 1)) * 3,
                           np.ones((num_neg_outliers, 1)) * 5)) +

                np.random.normal(scale=0.8, size=(num_neg_outliers, 2)))
    negatives = (np.full((kneg_regular, 2), 1.0) +
                 np.random.normal(scale=0.7, size=(kneg_regular, 2)))

    # Stack all items into the same array. To match y, first come all the
    # positives then all the negatives.
    X = np.vstack((positives, negatives, outliers))

    # Create labels. We have kpos +1s followed by kneg -1s.
    y = np.vstack((np.full((kpos, 1), 1.0), np.full((kneg, 1), -1.0)))

    # Stack X and y together so we can shuffle them together.
    Xy = np.hstack((X, y))
    Xy = np.random.permutation(np.hstack((X, y)))

    return Xy[:, 0:2], Xy[:, 2].reshape(-1, 1)


def plot_data_scatterplot(X, y, thetas=[]):
    """Plots data as a scatterplot.

    X: (k, n) data items.
    y: (k, 1) result (+1 or -1) for each data item in X.
    thetas: list of theta arrays to plot contours.

    Plots +1 data points as a green x, -1 as red o.
    """
    fig, ax = plt.subplots()
    fig.set_tight_layout(True)

    pos = [(X[k, 0], X[k, 1]) for k in range(X.shape[0]) if y[k, 0] == 1]
    neg = [(X[k, 0], X[k, 1]) for k in range(X.shape[0]) if y[k, 0] == -1]

    ax.scatter(*zip(*pos), c='darkgreen', marker='x')
    ax.scatter(*zip(*neg), c='red', marker='o', linewidths=0)

    for theta in thetas:
        xs = np.linspace(-2, 6, 200)
        ys = np.linspace(-2, 6, 200)
        xsgrid, ysgrid = np.meshgrid(xs, ys)
        plane = np.zeros_like(xsgrid)
        for i in range(xsgrid.shape[0]):
            for j in range(xsgrid.shape[1]):
                plane[i, j] = np.array([1, xsgrid[i, j], ysgrid[i, j]]).dot(
                    theta)
        ax.contour(xsgrid, ysgrid, plane, levels=[0])

    plt.show()


def L01_loss(X, y, theta):
    """Compute the L0/1 loss for the data X using theta.

    X: (k, n) k rows of data items, each having n features; augmented.
    y: (k, 1) correct classifications (+1 or -1) for each item.
    theta: (n, 1) regression parameters.

    Returns the total L0/1 loss over the whole data set. The total L0/1 loss
    is the number of mispredicted items (where y doesn't match yhat).
    """
    results = predict_binary(X, theta)
    return np.count_nonzero(results != y)


def search_best_L01_loss(X, y, theta_start=None,
                         npoints_per_t=150, tmargin=0.1):
    """Hacky exhaustive search for the best L0/1 loss for given X and y.

    X: (k, n) data items.
    y: (k, 1) result (+1 or -1) for each data item in X.
    theta_start: (3, 1) theta to start search from -- assuming
    npoints_per_t: number of points to search per dimension of theta.
    tmargin: search within [-tmargin, tmargin] of theta_start.

    Returns a pair best_theta, best_loss.
    """
    if theta_start is None:
        theta_start = np.array([[1], [1], [1]])

    k = X.shape[0]
    best_loss = k
    best_theta = theta_start

    assert theta_start.shape == (3, 1)
    t0_range = np.linspace(theta_start[0, 0] + tmargin,
                           theta_start[0, 0] - tmargin,
                           npoints_per_t)
    t1_range = np.linspace(theta_start[1, 0] + tmargin,
                           theta_start[1, 0] - tmargin,
                           npoints_per_t)
    t2_range = np.linspace(theta_start[2, 0] + tmargin,
                           theta_start[2, 0] - tmargin,
                           npoints_per_t)
    for t0 in t0_range:
        for t1 in t1_range:
            for t2 in t2_range:
                theta = np.array([[t0], [t1], [t2]])
                loss = L01_loss(X, y, theta)
                if loss < best_loss:
                    best_loss = loss
                    best_theta = theta

    return best_theta, best_loss


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--plot', action='store_true', default=False,
                           help='Produce scatterplot with fit contours')
    argparser.add_argument('--search01', action='store_true', default=False,
                           help='Run combinatorial search for best L0/1 loss')
    argparser.add_argument('--verbose-gd', action='store_true', default=False,
                           help='Verbose output from gradient-descent search')
    argparser.add_argument('--losstype',
                           choices=['square', 'hinge'],
                           default='square',
                           help='Type of loss function to use in gradient '
                                'descent')

    args = argparser.parse_args()

    # For reproducibility
    np.random.seed(42)

    X_train, y_train = generate_data(400, num_neg_outliers=20)
    print('X_train shape:', X_train.shape)
    print('y_train shape:', y_train.shape)

    NORMALIZE = False

    if NORMALIZE:
        X_train_normalized, mu, sigma = feature_normalize(X_train)
    else:
        X_train_normalized, mu, sigma = X_train, 0, 1

    X_train_augmented = np.hstack((np.ones((X_train.shape[0], 1)),
                                           X_train_normalized))
    print('X_train_augmented shape:', X_train_augmented.shape)

    # A pretty good theta determined by a long run of search_best_L01_loss.
    theta = np.array([-1.0607, 0.2793, 0.2664]).reshape(-1, 1)
    print('Initial theta:\n', theta)
    print('Initial loss:', L01_loss(X_train_augmented, y_train, theta))

    if args.search01:
        with Timer('searching for best L01 loss'):
            best_theta, best_loss = search_best_L01_loss(X_train_augmented,
                                                         y_train,
                                                         theta)
    else:
        best_theta, best_loss = theta, L01_loss(X_train_augmented, y_train,
                                                theta)

    print('Best theta:\n', best_theta)
    print('Best loss:', best_loss)

    if args.losstype == 'square':
        lossfunc = square_loss
        nsteps = 500
        learning_rate = 0.01
    elif args.losstype == 'hinge':
        lossfunc = hinge_loss
        nsteps = 1500
        learning_rate = 0.05
    else:
        raise UnimplementedError(args.losstype)

    print('Running GD with loss: {0}, for {1} steps, learning_rate={2}'.format
          (args.losstype, nsteps, learning_rate))
    gradient_descent_iter = gradient_descent(X_train_augmented, y_train,
                                             lossfunc,
                                             nsteps=nsteps,
                                             learning_rate=learning_rate)
    prev_loss = sys.float_info.max
    converge_step = 0
    for i, (theta, loss) in enumerate(gradient_descent_iter):
        if args.verbose_gd:
            print(i, ':', loss)
        if abs(loss - prev_loss) < 1e-5 and converge_step == 0:
            converge_step = i
        prev_loss = loss

    print('... loss converged at step {0}'.format(converge_step))
    print(theta)
    print(L01_loss(X_train_augmented, y_train, theta))
    if args.plot:
        print(best_theta)
        print(theta)
        plot_data_scatterplot(X_train, y_train, [best_theta, theta])