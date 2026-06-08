import { createRouter, createWebHistory } from 'vue-router'
import PlaceManagement from '../components/PlaceManagement.vue'
import ExistingPlacenames from '../components/ExistingPlacenames.vue'
import PlaceStats from '../components/PlaceStats.vue'

const routes = [
    {
        path: '/',
        redirect: '/place-management'
    },
    {
        path: '/place-management',
        name: 'PlaceManagement',
        component: PlaceManagement,
        meta: { title: '地名信息管理' }
    },
    {
        path: '/existing-placenames',
        name: 'ExistingPlacenames',
        component: ExistingPlacenames,
        meta: { title: '存量地名处理' }
    },
    {
        path: '/place-stats',
        name: 'PlaceStats',
        component: PlaceStats,
        meta: { title: '地名信息统计' }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router