from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
import cv2
import numpy as np
import torch
from typing import Union, Optional, Tuple, Iterable
import os
PathLike = Union[str, os.PathLike]

def config_rcnn(
        cfg_path: PathLike,
        weights_path: PathLike,
        conf_threshold: float
) -> DefaultPredictor:
    cfg = get_cfg()
    cfg.merge_from_file(cfg_path)
    cfg.MODEL.WEIGHTS = weights_path
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = conf_threshold
    if not torch.cuda.is_available():
        cfg.MODEL.DEVICE = 'cpu'

    # Initialize model
    predictor = DefaultPredictor(cfg)
    return predictor

def pred_rcnn(
        im: PathLike,
        predictor: DefaultPredictor
) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor], Optional[torch.Tensor]]:

    im = cv2.imread(im)

    if im is not None:
        if im.shape[-1] == 4:
            im = cv2.cvtColor(im, cv2.COLOR_BGRA2BGR)
    else:
        return None, None, None

    outputs = predictor(im)
    instances = outputs['instances']
    pred_classes = instances.pred_classes.detach().cpu()  # tensor
    pred_boxes = instances.pred_boxes.tensor.detach().cpu()  # Boxes object
    pred_scores = instances.scores  # tensor

    return pred_boxes, pred_classes, pred_scores


def find_element_type(
    pred_boxes: torch.Tensor,
    pred_classes: torch.Tensor,
    bbox_type: str = 'button',
) -> Tuple[torch.Tensor, torch.Tensor]:

    class_dict = {0: 'logo', 1: 'input', 2: 'button', 3: 'label', 4: 'block'}
    inv_class_dict = {v: k for k, v in class_dict.items()}
    assert bbox_type in ['logo', 'input', 'button', 'label', 'block']

    pred_boxes_after = pred_boxes[pred_classes == inv_class_dict[bbox_type]]
    pred_classes_after = pred_classes[pred_classes == inv_class_dict[bbox_type]]
    return pred_boxes_after, pred_classes_after




