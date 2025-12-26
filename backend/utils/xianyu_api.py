"""
闲鱼管家开放平台 Python SDK
功能：商品管理、类目查询、属性查询等
"""
import hashlib
import time
import requests
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class GoofishConfig:
    """闲鱼管家配置"""
    app_key: str
    app_secret: str
    base_url: str = "https://open.goofish.pro"  # 注意是 open.goofish.pro
    seller_id: Optional[str] = None
    connect_timeout: int = 30
    read_timeout: int = 60
    verify_ssl: bool = True  # SSL 证书验证，macOS 有问题时可设为 False


class SignUtil:
    """签名工具类"""
    
    @staticmethod
    def md5(text: str) -> str:
        """计算MD5"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_sign(app_key: str, app_secret: str, body_json: str, timestamp: int) -> str:
        """
        生成签名
        签名规则: sign = md5("appKey,bodyMd5,timestamp,appSecret")
        """
        body_md5 = SignUtil.md5(body_json)
        sign_str = f"{app_key},{body_md5},{timestamp},{app_secret}"
        return SignUtil.md5(sign_str)
    
    @staticmethod
    def generate_sign_with_seller(app_key: str, app_secret: str, body_json: str, 
                                  timestamp: int, seller_id: str) -> str:
        """
        生成签名（商务对接版本）
        签名规则: sign = md5("appKey,bodyMd5,timestamp,sellerId,appSecret")
        """
        body_md5 = SignUtil.md5(body_json)
        sign_str = f"{app_key},{body_md5},{timestamp},{seller_id},{app_secret}"
        return SignUtil.md5(sign_str)


class GoofishClient:
    """闲鱼管家 HTTP 客户端"""
    
    def __init__(self, config: GoofishConfig):
        self.config = config
        self.session = requests.Session()
    
    def post(self, path: str, request_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送 POST 请求
        
        Args:
            path: API 路径
            request_body: 请求体
            
        Returns:
            响应数据
        """
        import json
        
        body_json = json.dumps(request_body or {}, ensure_ascii=False)
        timestamp = int(time.time())
        
        # 生成签名
        if self.config.seller_id:
            sign = SignUtil.generate_sign_with_seller(
                self.config.app_key,
                self.config.app_secret,
                body_json,
                timestamp,
                self.config.seller_id
            )
        else:
            sign = SignUtil.generate_sign(
                self.config.app_key,
                self.config.app_secret,
                body_json,
                timestamp
            )
        
        # 构建 URL
        url = f"{self.config.base_url}{path}"
        params = {
            'appid': self.config.app_key,
            'timestamp': str(timestamp),
            'sign': sign
        }
        
        if self.config.seller_id:
            params['seller_id'] = self.config.seller_id
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Goofish-Python-SDK/1.0.0'
        }
        
        logger.info(f"请求 URL: {url}")
        logger.info(f"请求参数: {params}")
        logger.info(f"请求体: {body_json}")
        
        try:
            # 使用配置的 SSL 验证选项（macOS 证书问题时可以禁用）
            response = self.session.post(
                url,
                params=params,
                headers=headers,
                data=body_json.encode('utf-8'),
                timeout=(self.config.connect_timeout, self.config.read_timeout),
                verify=self.config.verify_ssl
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"响应: {result}")
            
            # 检查响应码（闲鱼API成功码是0，不是200）
            code = result.get('code')
            if code != 0 and code != 200:
                error_msg = result.get('msg', '未知错误')
                logger.error(f"API错误: {error_msg}")
                raise GoofishException(code, error_msg)
            
            return result.get('data', {})
            
        except requests.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise GoofishException(-1, f"请求失败: {str(e)}")
    
    def close(self):
        """关闭客户端"""
        self.session.close()


class GoofishException(Exception):
    """闲鱼管家异常"""
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# ==================== 数据模型 ====================

@dataclass
class PublishShop:
    """发布店铺"""
    userName: str  # 会员名
    province: int  # 省份代码
    city: int  # 城市代码
    district: int  # 区县代码
    title: str  # 商品标题
    content: str  # 商品描述
    images: List[str]  # 图片URL列表


@dataclass
class CreateProductRequest:
    """创建商品请求"""
    itemBizType: int  # 商品业务类型
    spBizType: int  # SP业务类型
    channelCatId: str  # 类目ID
    price: int  # 价格（分）
    expressFee: int  # 运费（分）
    stock: int  # 库存
    stuffStatus: int  # 成色
    publishShop: List[Dict[str, Any]]  # 发布店铺列表
    
    def to_dict(self):
        """转换为下划线命名的字典（API要求）"""
        # 手动映射字段名，转换为下划线命名
        data = {
            'item_biz_type': self.itemBizType,
            'sp_biz_type': self.spBizType,
            'channel_cat_id': self.channelCatId,
            'price': self.price,
            'express_fee': self.expressFee,
            'stock': self.stock,
            'stuff_status': self.stuffStatus,
            'publish_shop': []
        }
        
        # 转换 publishShop
        if self.publishShop:
            if isinstance(self.publishShop[0], PublishShop):
                data['publish_shop'] = [self._convert_shop(shop) for shop in self.publishShop]
            else:
                data['publish_shop'] = self.publishShop
        
        return data
    
    def _convert_shop(self, shop: 'PublishShop') -> dict:
        """转换店铺对象为字典（user_name需要下划线）"""
        return {
            'user_name': shop.userName,
            'province': shop.province,
            'city': shop.city,
            'district': shop.district,
            'title': shop.title,
            'content': shop.content,
            'images': shop.images
        }


@dataclass
class CreateProductResponse:
    """创建商品响应"""
    productId: Optional[int] = None
    productStatus: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建（处理下划线命名）"""
        return cls(
            productId=data.get('product_id'),
            productStatus=data.get('product_status')
        )


@dataclass
class PublishProductRequest:
    """上架商品请求"""
    productId: int
    userName: List[str]
    
    def to_dict(self):
        return {
            'product_id': self.productId,
            'user_name': self.userName
        }


@dataclass
class PublishProductResponse:
    """上架商品响应"""
    success: bool = True


@dataclass
class DownShelfProductRequest:
    """下架商品请求"""
    productId: int
    
    def to_dict(self):
        return {'product_id': self.productId}


@dataclass
class DownShelfProductResponse:
    """下架商品响应"""
    success: bool = True


@dataclass
class DeleteProductRequest:
    """删除商品请求"""
    productId: int
    
    def to_dict(self):
        return {'product_id': self.productId}


@dataclass
class DeleteProductResponse:
    """删除商品响应"""
    success: bool = True


@dataclass
class ProductListRequest:
    """商品列表请求"""
    pageNo: int = 1
    pageSize: int = 50
    productStatus: Optional[int] = None  # 商品状态
    updateTime: Optional[List[int]] = None  # 更新时间范围[开始,结束]
    
    def to_dict(self):
        data = {
            'page_no': self.pageNo,
            'page_size': self.pageSize
        }
        if self.productStatus is not None:
            data['product_status'] = self.productStatus
        if self.updateTime:
            data['update_time'] = self.updateTime
        return data


@dataclass
class ProductItem:
    """商品项"""
    productId: int
    title: str
    outerId: Optional[str] = None
    price: Optional[int] = None
    originalPrice: Optional[int] = None
    stock: Optional[int] = None
    sold: Optional[int] = None
    productStatus: Optional[int] = None
    itemBizType: Optional[int] = None
    spBizType: Optional[int] = None
    channelCatId: Optional[str] = None
    districtId: Optional[int] = None
    stuffStatus: Optional[int] = None
    expressFee: Optional[int] = None
    specType: Optional[int] = None
    source: Optional[int] = None
    specifyPublishTime: Optional[int] = None
    onlineTime: Optional[int] = None
    offlineTime: Optional[int] = None
    soldTime: Optional[int] = None
    updateTime: Optional[int] = None
    createTime: Optional[int] = None


@dataclass
class ProductListResponse:
    """商品列表响应"""
    list: List[Dict[str, Any]]
    total: int


@dataclass
class ProductDetailRequest:
    """商品详情请求"""
    productId: int
    
    def to_dict(self):
        return {'product_id': self.productId}


@dataclass
class CategoryListRequest:
    """类目列表请求"""
    parentId: Optional[str] = None
    
    def to_dict(self):
        data = {}
        if self.parentId:
            data['parent_id'] = self.parentId
        return data


@dataclass
class PropertyListRequest:
    """属性列表请求"""
    channelCatId: str
    
    def to_dict(self):
        return {'channel_cat_id': self.channelCatId}


# ==================== 商品服务 ====================

class ProductService:
    """商品服务"""
    
    def __init__(self, client: GoofishClient):
        self.client = client
    
    def create_product(self, request: CreateProductRequest) -> CreateProductResponse:
        """创建商品"""
        data = self.client.post('/api/open/product/create', request.to_dict())
        return CreateProductResponse.from_dict(data)
    
    def publish_product(self, request: PublishProductRequest) -> PublishProductResponse:
        """上架商品"""
        self.client.post('/api/open/product/publish', request.to_dict())
        return PublishProductResponse()
    
    def downshelf_product(self, request: DownShelfProductRequest) -> DownShelfProductResponse:
        """下架商品"""
        self.client.post('/api/open/product/downShelf', request.to_dict())
        return DownShelfProductResponse()
    
    def delete_product(self, request: DeleteProductRequest) -> DeleteProductResponse:
        """删除商品（仅草稿箱/待发布状态）"""
        self.client.post('/api/open/product/delete', request.to_dict())
        return DeleteProductResponse()
    
    def list_product(self, request: ProductListRequest) -> ProductListResponse:
        """查询商品列表"""
        data = self.client.post('/api/open/product/list', request.to_dict())
        return ProductListResponse(
            list=data.get('list', []),
            total=data.get('total', 0)
        )
    
    def get_product_detail(self, request: ProductDetailRequest) -> Dict[str, Any]:
        """查询商品详情"""
        return self.client.post('/api/open/product/detail', request.to_dict())
    
    def get_category_list(self, request: CategoryListRequest) -> Dict[str, Any]:
        """查询类目列表"""
        return self.client.post('/api/open/product/category/list', request.to_dict())
    
    def get_property_list(self, request: PropertyListRequest) -> Dict[str, Any]:
        """查询属性列表"""
        return self.client.post('/api/open/product/pv/list', request.to_dict())


# ==================== SDK 主入口 ====================

class GoofishSDK:
    """闲鱼管家 SDK 主入口"""
    
    def __init__(self, config: GoofishConfig):
        self.config = config
        self.client = GoofishClient(config)
        self._product_service = ProductService(self.client)
    
    def product(self) -> ProductService:
        """获取商品服务"""
        return self._product_service
    
    def close(self):
        """关闭 SDK"""
        self.client.close()

