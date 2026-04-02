import { createRouter, createWebHistory } from 'vue-router';
import RagWorkspace from '../views/RagWorkspace.vue';

const routes = [
  {
    path: '/',
    name: 'rag-workspace',
    component: RagWorkspace
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
