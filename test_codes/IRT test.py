print("123")
import math
result= math.sqrt(16)
print(result)
import numpy as np
print("******")
arr = np.arry([1,2,3])
print(arr)
from pyirt import irt
np.random.seed(42)
theta_true = np.random.normal(0, 1, 5)
item_parameters = np.random.unifprm(-2, 2, (10, 2))
responses = irt.simulate_responses(item_parameters, theta_true)

# modelscope download --model PaddlePaddle/PP-DocLayout_plus-L  --local_dir ./PP-DocLayout_plus-L