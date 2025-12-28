import { createRouter, createWebHistory } from 'vue-router'
import MediaLibrary from '../views/MediaLibrary.vue'
import MappingManage from '../views/MappingManage.vue'
import LinkRecords from '../views/LinkRecords.vue'
import Config from '../views/Config.vue'
import ShareLinks from '../views/ShareLinks.vue'
import MediaRequests from '../views/MediaRequests.vue'
import XianyuProducts from '../views/XianyuProducts.vue'
import XianyuCreateProduct from '../views/XianyuCreateProduct.vue'
import XianyuAutoWorkflow from '../views/XianyuAutoWorkflow.vue'

const routes = [
  {
    path: '/',
    redirect: '/media'
  },
  {
    path: '/media',
    name: 'MediaLibrary',
    component: MediaLibrary
  },
  {
    path: '/mappings',
    name: 'Mappings',
    component: MappingManage
  },
  {
    path: '/records',
    name: 'Records',
    component: LinkRecords
  },
  {
    path: '/share-links',
    name: 'ShareLinks',
    component: ShareLinks
  },
  {
    path: '/media-requests',
    name: 'MediaRequests',
    component: MediaRequests
  },
  {
    path: '/config',
    name: 'Config',
    component: Config
  },
  {
    path: '/xianyu/products',
    name: 'XianyuProducts',
    component: XianyuProducts
  },
  {
    path: '/xianyu/create-product',
    name: 'XianyuCreateProduct',
    component: XianyuCreateProduct
  },
  {
    path: '/xianyu/auto-workflow',
    name: 'XianyuAutoWorkflow',
    component: XianyuAutoWorkflow
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
