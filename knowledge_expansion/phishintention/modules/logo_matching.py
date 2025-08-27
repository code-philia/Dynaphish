from PIL import Image, ImageOps
from torchvision import transforms
import torch
from torch.backends import cudnn
import os
import numpy as np
from collections import OrderedDict
from tqdm import tqdm
from tldextract import tldextract
import pickle
from dataclasses import dataclass, field
from ..utils import brand_converter, resolution_alignment, l2_norm
from .models2 import KNOWN_MODELS, ResNetV2
from ..ocr_lib import ModelBuilder, get_vocabulary
from typing import List, Dict, Union, Tuple
from numpy.typing import ArrayLike, NDArray
PathLike = Union[str, os.PathLike]

COUNTRY_TLDs = [
    ".af",
    ".ax",
    ".al",
    ".dz",
    ".as",
    ".ad",
    ".ao",
    ".ai",
    ".aq",
    ".ag",
    ".ar",
    ".am",
    ".aw",
    ".ac",
    ".au",
    ".at",
    ".az",
    ".bs",
    ".bh",
    ".bd",
    ".bb",
    ".eus",
    ".by",
    ".be",
    ".bz",
    ".bj",
    ".bm",
    ".bt",
    ".bo",
    ".bq",".an",".nl",
    ".ba",
    ".bw",
    ".bv",
    ".br",
    ".io",
    ".vg",
    ".bn",
    ".bg",
    ".bf",
    ".mm",
    ".bi",
    ".kh",
    ".cm",
    ".ca",
    ".cv",
    ".cat",
    ".ky",
    ".cf",
    ".td",
    ".cl",
    ".cn",
    ".cx",
    ".cc",
    ".co",
    ".km",
    ".cd",
    ".cg",
    ".ck",
    ".cr",
    ".ci",
    ".hr",
    ".cu",
    ".cw",
    ".cy",
    ".cz",
    ".dk",
    ".dj",
    ".dm",
    ".do",
    ".tl",".tp",
    ".ec",
    ".eg",
    ".sv",
    ".gq",
    ".er",
    ".ee",
    ".et",
    ".eu",
    ".fk",
    ".fo",
    ".fm",
    ".fj",
    ".fi",
    ".fr",
    ".gf",
    ".pf",
    ".tf",
    ".ga",
    ".gal",
    ".gm",
    ".ps",
    ".ge",
    ".de",
    ".gh",
    ".gi",
    ".gr",
    ".gl",
    ".gd",
    ".gp",
    ".gu",
    ".gt",
    ".gg",
    ".gn",
    ".gw",
    ".gy",
    ".ht",
    ".hm",
    ".hn",
    ".hk",
    ".hu",
    ".is",
    ".in",
    ".id",
    ".ir",
    ".iq",
    ".ie",
    ".im",
    ".il",
    ".it",
    ".jm",
    ".jp",
    ".je",
    ".jo",
    ".kz",
    ".ke",
    ".ki",
    ".kw",
    ".kg",
    ".la",
    ".lv",
    ".lb",
    ".ls",
    ".lr",
    ".ly",
    ".li",
    ".lt",
    ".lu",
    ".mo",
    ".mk",
    ".mg",
    ".mw",
    ".my",
    ".mv",
    ".ml",
    ".mt",
    ".mh",
    ".mq",
    ".mr",
    ".mu",
    ".yt",
    ".mx",
    ".md",
    ".mc",
    ".mn",
    ".me",
    ".ms",
    ".ma",
    ".mz",
    ".mm",
    ".na",
    ".nr",
    ".np",
    ".nl",
    ".nc",
    ".nz",
    ".ni",
    ".ne",
    ".ng",
    ".nu",
    ".nf",
    ".nc",".tr",
    ".kp",
    ".mp",
    ".no",
    ".om",
    ".pk",
    ".pw",
    ".ps",
    ".pa",
    ".pg",
    ".py",
    ".pe",
    ".ph",
    ".pn",
    ".pl",
    ".pt",
    ".pr",
    ".qa",
    ".ro",
    ".ru",
    ".rw",
    ".re",
    ".bq",".an",
    ".bl",".gp",".fr",
    ".sh",
    ".kn",
    ".lc",
    ".mf",".gp",".fr",
    ".pm",
    ".vc",
    ".ws",
    ".sm",
    ".st",
    ".sa",
    ".sn",
    ".rs",
    ".sc",
    ".sl",
    ".sg",
    ".bq",".an",".nl",
    ".sx",".an",
    ".sk",
    ".si",
    ".sb",
    ".so",
    ".so",
    ".za",
    ".gs",
    ".kr",
    ".ss",
    ".es",
    ".lk",
    ".sd",
    ".sr",
    ".sj",
    ".sz",
    ".se",
    ".ch",
    ".sy",
    ".tw",
    ".tj",
    ".tz",
    ".th",
    ".tg",
    ".tk",
    ".to",
    ".tt",
    ".tn",
    ".tr",
    ".tm",
    ".tc",
    ".tv",
    ".ug",
    ".ua",
    ".ae",
    ".uk",
    ".us",
    ".vi",
    ".uy",
    ".uz",
    ".vu",
    ".va",
    ".ve",
    ".vn",
    ".wf",
    ".eh",
    ".ma",
    ".ye",
    ".zm",
    ".zw"
]

@dataclass
class DataInfo:
    voc_type: str
    EOS: str = "EOS"
    PADDING: str = "PADDING"
    UNKNOWN: str = "UNKNOWN"

    voc: List[str] = field(init=False)
    char2id: Dict[str, int] = field(init=False)
    id2char: Dict[int, str] = field(init=False)
    rec_num_classes: int = field(init=False)

    def __post_init__(self):
        assert self.voc_type in ["LOWERCASE", "ALLCASES", "ALLCASES_SYMBOLS"]
        self.voc = get_vocabulary(self.voc_type, EOS=self.EOS, PADDING=self.PADDING, UNKNOWN=self.UNKNOWN)
        self.char2id = {ch: i for i, ch in enumerate(self.voc)}
        self.id2char = {i: ch for i, ch in enumerate(self.voc)}
        self.rec_num_classes = len(self.voc)

def ocr_model_config(
        weights_path: PathLike
) -> ModelBuilder:
    np.random.seed(1234)
    torch.manual_seed(1234)
    torch.cuda.manual_seed(1234)
    torch.cuda.manual_seed_all(1234)
    cudnn.benchmark = True
    torch.backends.cudnn.deterministic = True

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device == 'cuda':
        torch.set_default_tensor_type('torch.cuda.FloatTensor')
    else:
        torch.set_default_tensor_type('torch.FloatTensor')

    dataset_info = DataInfo('ALLCASES_SYMBOLS')
    model = ModelBuilder(arch='ResNet_ASTER',
                         rec_num_classes=dataset_info.rec_num_classes,
                         sDim=512, attDim=512, max_len_labels=100,
                         eos=dataset_info.char2id[dataset_info.EOS],
                         STN_ON=True)

    # Load from checkpoint
    weights_path = torch.load(weights_path, map_location='cpu')
    model.load_state_dict(weights_path['state_dict'])

    if device == 'cuda':
        model = model.to(device)
    return model

def siamese_model_config(
        num_classes: int,
        weights_path: PathLike
) -> ResNetV2:
    # Initialize model
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = KNOWN_MODELS["BiT-M-R50x1"](head_size=num_classes, zero_head=True)

    # Load weights
    weights = torch.load(weights_path, map_location='cpu')
    weights = weights['model'] if 'model' in weights.keys() else weights
    new_state_dict = OrderedDict()
    for k, v in weights.items():
        if k.startswith('module'):
            name = k.split('module.')[1]
        else:
            name = k
        new_state_dict[name] = v

    model.load_state_dict(new_state_dict)
    model.to(device)
    model.eval()

    return model


def image_process(
        image_path: Union[PathLike, Image.Image],
        imgH: int =32,
        imgW: int =100,
        keep_ratio: bool =False,
        min_ratio: int=1
) -> torch.Tensor:
    img = Image.open(image_path).convert('RGB') if isinstance(image_path, str) else image_path.convert('RGB')

    if keep_ratio:
        w, h = img.size
        ratio = w / float(h)
        imgW = int(np.floor(ratio * imgH))
        imgW = max(imgH * min_ratio, imgW)

    img = img.resize((imgW, imgH), Image.BILINEAR)
    img = transforms.ToTensor()(img)
    img.sub_(0.5).div_(0.5)

    return img


@torch.inference_mode()
def ocr_main(
        image_path: Union[PathLike, Image.Image],
        model: ModelBuilder
) -> torch.Tensor:
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    # Evaluation
    model.eval()

    img = image_process(image_path)
    with torch.no_grad():
        img = img.to(device)
    input_dict = {}
    input_dict['images'] = img.unsqueeze(0)

    dataset_info = DataInfo('ALLCASES_SYMBOLS')
    rec_targets = torch.IntTensor(1, 100).fill_(1)
    rec_targets[:, 100 - 1] = dataset_info.char2id[dataset_info.EOS]
    input_dict['rec_targets'] = rec_targets.to(device)
    input_dict['rec_lengths'] = [100]

    with torch.no_grad():
        features, decoder_feat = model.features(input_dict)
    features = features.detach().cpu()
    decoder_feat = decoder_feat.detach().cpu()
    features = torch.mean(features, dim=1)

    return features


@torch.inference_mode()
def get_ocr_aided_siamese_embedding(
        img: Union[PathLike, Image.Image],
        model: ResNetV2,
        ocr_model: ModelBuilder,
) -> NDArray:
    img_size = 224
    mean = [0.5, 0.5, 0.5]
    std = [0.5, 0.5, 0.5]
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    img_transforms = transforms.Compose(
        [transforms.ToTensor(),
         transforms.Normalize(mean=mean, std=std),
     ])

    img = Image.open(img) if isinstance(img, str) else img
    img = img.convert("RGBA").convert("RGB")

    ## Resize the image while keeping the original aspect ratio
    pad_color = (255, 255, 255)
    img = ImageOps.expand(img, (
        (max(img.size) - img.size[0]) // 2, (max(img.size) - img.size[1]) // 2,
        (max(img.size) - img.size[0]) // 2, (max(img.size) - img.size[1]) // 2), fill=pad_color)

    img = img.resize((img_size, img_size))

    # Predict the embedding
    # get ocr embedding from pretrained paddleOCR
    with torch.no_grad():
        ocr_emb = ocr_main(image_path=img, model=ocr_model)
        ocr_emb = ocr_emb[0]
        ocr_emb = ocr_emb[None, ...].to(device)  # remove batch dimension

    # Predict the embedding
    with torch.no_grad():
        img = img_transforms(img)
        img = img[None, ...].to(device)
        logo_feat = model.features(img, ocr_emb)
        logo_feat = l2_norm(logo_feat).squeeze(0).cpu().numpy()  # L2-normalization final shape is (2560,)

    return logo_feat

def chunked_dot(
        logo_feat_list: NDArray,
        img_feat: NDArray,
        chunk_size: int=128
) -> List[float]:
    sim_list = []

    for start in range(0, logo_feat_list.shape[0], chunk_size):
        end = start + chunk_size
        chunk = logo_feat_list[start:end]
        sim_chunk = np.dot(chunk, img_feat.T)  # shape: (chunk_size, M)
        sim_list.extend(sim_chunk)

    return sim_list

def cache_reference_list(
        model: ResNetV2,
        ocr_model: ModelBuilder,
        targetlist_path: PathLike
) -> Tuple[NDArray, NDArray]:

    #  Prediction for targetlists
    logo_feat_list = []
    file_name_list = []

    for target in tqdm(os.listdir(targetlist_path)):
        if target.startswith('.'):  # skip hidden files
            continue
        for logo_path in os.listdir(os.path.join(targetlist_path, target)):
            if logo_path.endswith('.png') or logo_path.endswith('.jpeg') or logo_path.endswith('.jpg') or logo_path.endswith('.PNG') \
                    or logo_path.endswith('.JPG') or logo_path.endswith('.JPEG'):
                if logo_path.startswith('loginpage') or logo_path.startswith('homepage'):  # skip homepage/loginpage
                    continue
                logo_feat_list.append(get_ocr_aided_siamese_embedding(
                    img=os.path.join(targetlist_path, target, logo_path),
                    model=model,
                    ocr_model=ocr_model
                  ))
                file_name_list.append(str(os.path.join(targetlist_path, target, logo_path)))

    return np.asarray(logo_feat_list), \
           np.asarray(file_name_list)


