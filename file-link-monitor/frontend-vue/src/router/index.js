import { createRouter, createWebHistory } from 'vue-router'
import MappingManage from '../views/MappingManage.vue'
import LinkRecords from '../views/LinkRecords.vue'
import DirectoryTree from '../views/DirectoryTree.vue'
import Config from '../views/Config.vue'
import ShareLinks from '../views/ShareLinks.vue'

const routes = [
  {
    path: '/',
    redirect: '/mappings'
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
    path: '/tree',
    name: 'Tree',
    component: DirectoryTree
  },
  {
    path: '/share-links',
    name: 'ShareLinks',
    component: ShareLinks
  },
  {
    path: '/config',
    name: 'Config',
    component: Config
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
