import random
import time
import unittest

import cv2
import numpy as np

from facelib.FacialMesh import _predict_3d_mesh, get_mesh_landmarks, get_texture, get_mesh_mask
from nnlib import nnlib
from facelib import LandmarksExtractor, S3FDExtractor
from samplelib import SampleLoader, SampleType


class MyTestCase(unittest.TestCase):
    def test_something(self):
        t0 = time.time()
        source_image = cv2.imread('../../imagelib/test/test_src/carrey/carrey.jpg')
        print(time.time() - t0, 'loaded image')
        print('source_image type:', source_image.dtype)
        print('source_image shape:', source_image.shape)
        im = np.copy(source_image)

        device_config = nnlib.DeviceConfig(cpu_only=True)
        nnlib.import_all(device_config)
        landmark_extractor = LandmarksExtractor(nnlib.keras)
        s3fd_extractor = S3FDExtractor()

        rects = s3fd_extractor.extract(input_image=im, is_bgr=True)
        print('rects:', rects)
        bbox = rects[0]  # bounding box
        l, t, r, b = bbox

        print(time.time() - t0, 'got bbox')
        landmark_extractor.__enter__()
        s3fd_extractor.__enter__()

        landmarks = landmark_extractor.extract(input_image=im, rects=rects, second_pass_extractor=s3fd_extractor,
                                               is_bgr=True)[-1]
        s3fd_extractor.__exit__()
        landmark_extractor.__exit__()
        print(time.time() - t0, 'got landmarks')
        print('landmarks shape:', np.shape(landmarks))

        mesh_points, isomap, mask, tvi = get_mesh_landmarks(landmarks, im)
        print(time.time() - t0, 'got mesh')
        print('mesh_points:', np.shape(mesh_points))

        cv2.namedWindow('test output', cv2.WINDOW_NORMAL)

        # Draw the bounding box
        cv2.rectangle(im, (l, t), (r, b), (0, 0, 255), thickness=2)

        # Draw the 3D mesh
        # im_zoom = np.copy(im)
        # m = 128
        # # im_zoom = cv2.resize(im_zoom, (m*im.shape[1], m*im.shape[0]))
        # im_zoom = np.zeros((m*im.shape[0], m*im.shape[1], 3), dtype=np.float32)
        # triangles = mesh_points[tvi]
        # np.rint(triangles, out=triangles)
        # triangles = m * triangles.astype(np.int32)
        # cv2.polylines(im_zoom, triangles, True, (0, 0, 255), 2)

        # mouth = [
        #     398,
        #     3446,
        #     408,
        #     3253,
        #     406,
        #     3164,
        #     404,
        #     3115,
        #     402,
        #     3257,
        #     399,
        #     3374,
        #     442,
        #     3376,
        #     813,
        #     3260,
        #     815,
        #     3119,
        #     817,
        #     3167,
        #     819,
        #     3256,
        #     821,
        #     3447,
        #     812,
        #     3427,
        #     823,
        #     3332,
        #     826,
        #     3157,
        #     828,
        #     3212,
        #     830,
        #     3382,
        #     832,
        #     3391,
        #     423,
        #     3388,
        #     420,
        #     3381,
        #     418,
        #     3211,
        #     416,
        #     3155,
        #     414,
        #     3331,
        #     410,
        #     3426,
        # ]

        # mouth_poly = mesh_points[mouth]
        # np.rint(mouth_poly, out=mouth_poly)
        # mouth_poly = mouth_poly.astype(np.int32)
        #
        # cv2.fillPoly(im_zoom, [m*mouth_poly], (64, 64, 0))

        for i, pt in enumerate(mesh_points):
            # if 165 < pt[0] < 256 and 346 < pt[1] < 378:
            #     print(i, pt)
            #     # cv2.circle(im_zoom, (int(m*pt[0]), int(m*pt[1])), 1, (255, 255, 255), thickness=-1)
            #     cv2.putText(im_zoom, str(i), (int(m*pt[0]), int(m*pt[1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.circle(im, (int(pt[0]), int(pt[1])), 1, (255, 255, 255), thickness=-1)

        # im_zoom = im_zoom[m*346:m*378, m*165:m*256, ...]
        # cv2.imshow('test output', im_zoom)
        # cv2.waitKey(0)

        # Draw the landmarks
        for i, pt in enumerate(landmarks):
            cv2.circle(im, (int(pt[0]), int(pt[1])), 3, (0, 255, 0), thickness=-1)

        cv2.imshow('test output', im)
        cv2.waitKey(0)

        cv2.imshow('test output', isomap.transpose([1, 0, 2]))
        cv2.waitKey(0)

        im = np.copy(source_image).astype(np.float32) / 255.0

        cv2.imshow('test output', mask)
        cv2.waitKey(0)

        # cv2.imshow('test output', np.concatenate((im, mask), -1))
        cv2.imshow('test output', mask * im)
        cv2.waitKey(0)

        cv2.destroyAllWindows()

    def test_compare_hull_mask_with_mesh_mask(self):
        src_samples = SampleLoader.load(SampleType.FACE, './aligned_carrey', None)

        sample_grid = self.get_sample_grid(src_samples)
        display_grid = []
        for sample_row in sample_grid:
            display_row = []
            for sample in sample_row:
                src_img = sample.load_bgr()
                src_hull_mask = sample.load_image_hull_mask()

                src_landmarks = sample.landmarks
                src_mesh_mask = get_mesh_mask(src_landmarks, src_img)

                results = np.concatenate((src_img, src_hull_mask * src_img, src_mesh_mask * src_img), axis=1)
                display_row.append(results)
            display_grid.append(np.concatenate(display_row, axis=1))
        output_grid = np.concatenate(display_grid, axis=0)

        cv2.namedWindow('test output', cv2.WINDOW_NORMAL)
        cv2.imshow('test output', output_grid)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    @staticmethod
    def get_sample_grid(src_samples):
        pitch_yaw = np.array([[sample.pitch_yaw_roll[0], sample.pitch_yaw_roll[1]] for sample in src_samples])
        pitch_yaw = (pitch_yaw - np.mean(pitch_yaw, axis=0)) / np.std(pitch_yaw, axis=0)

        # theta_r = np.stack((np.arctan2(pitch_yaw[:, 0], pitch_yaw[:, 1]), np.hypot(pitch_yaw[:, 0], pitch_yaw[:, 1])), axis=-1)

        grid = [[[1, 1], [1, 0], [1, -1]],
                [[0, 1], [0, 0], [0, -1]],
                [[-1, 1], [-1, 0], [-1, -1]]]

        grid_samples = []
        for row in grid:
            row_samples = []
            for item in row:
                # print(item, pitch_yaw[np.sum(np.square(np.abs(pitch_yaw - item)), 1).argmin()])
                row_samples.append(src_samples[np.sum(np.square(np.abs(pitch_yaw - item)), 1).argmin()])
            grid_samples.append(row_samples)
        return grid_samples



if __name__ == '__main__':
    unittest.main()
