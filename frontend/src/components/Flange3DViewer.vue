<template>
  <div class="flange-3d-viewer" ref="containerRef">
    <div class="viewer-toolbar">
      <div class="toolbar-left">
        <div class="mode-selector">
          <span class="mode-label">显示模式:</span>
          <div class="mode-buttons">
            <button
              v-for="mode in displayModes"
              :key="mode.value"
              :class="['mode-btn', { active: currentMode === mode.value }]"
              @click="switchMode(mode.value)"
            >
              {{ mode.label }}
            </button>
          </div>
        </div>
      </div>
      <div class="toolbar-right">
        <button class="action-btn" :class="{ active: isExploded }" @click="toggleExplosion">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"></path>
          </svg>
          爆炸图
        </button>
        <button class="action-btn" :class="{ active: autoRotate }" @click="toggleAutoRotate">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          自动旋转
        </button>
        <button class="action-btn" @click="resetView">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
            <path d="M3 3v5h5"></path>
          </svg>
          重置视图
        </button>
      </div>
    </div>

    <div class="viewer-canvas" ref="canvasRef"></div>

    <div class="viewer-legend">
      <div class="legend-title" v-if="currentMode === 'status'">状态图例</div>
      <div class="legend-title" v-else-if="currentMode === 'hi'">健康度HI图例</div>
      <div class="legend-title" v-else-if="currentMode === 'risk'">风险图例</div>
      <div class="legend-items">
        <template v-if="currentMode === 'status'">
          <div v-for="(label, code) in statusLegend" :key="code" class="legend-item">
            <span class="legend-dot" :style="{ background: statusColors[Number(code)] }"></span>
            <span class="legend-text">{{ label }}</span>
          </div>
        </template>
        <template v-else-if="currentMode === 'hi'">
          <div class="gradient-bar">
            <div class="gradient-fill" :style="{ background: hiGradient }"></div>
          </div>
          <div class="gradient-labels">
            <span>0</span>
            <span>50</span>
            <span>100</span>
          </div>
        </template>
        <template v-else-if="currentMode === 'risk'">
          <div v-for="(label, level) in riskLegend" :key="level" class="legend-item">
            <span class="legend-dot" :style="{ background: riskColors[level] }"></span>
            <span class="legend-text">{{ label }}</span>
          </div>
        </template>
      </div>
    </div>

    <div class="viewer-info" v-if="selectedBolt">
      <div class="info-header">
        <span class="info-title">螺栓信息</span>
        <button class="close-btn" @click="selectedBolt = null">×</button>
      </div>
      <div class="info-content">
        <div class="info-row">
          <span class="info-label">螺栓ID:</span>
          <span class="info-value">{{ selectedBolt.bolt_id }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">状态:</span>
          <span class="info-value" :style="{ color: statusColors[selectedBolt.status_code || 0] }">
            {{ statusLegend[selectedBolt.status_code || 0] }}
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">健康度HI:</span>
          <span class="info-value hi-value">
            {{ selectedBolt.hi_score?.toFixed(1) || '-' }}
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">风险等级:</span>
          <span class="info-value" :style="{ color: riskColors[selectedBolt.risk_level || 'low'] }">
            {{ riskLegend[selectedBolt.risk_level || 'low'] }}
          </span>
        </div>
        <div class="info-row" v-if="selectedBolt.confidence">
          <span class="info-label">置信度:</span>
          <span class="info-value">{{ (selectedBolt.confidence * 100).toFixed(1) }}%</span>
        </div>
        <div class="info-row" v-if="selectedBolt.diagnosis">
          <span class="info-label">诊断:</span>
          <span class="info-value">{{ selectedBolt.diagnosis }}</span>
        </div>
      </div>
    </div>

    <div class="viewer-stats">
      <span>螺栓数量: {{ boltCount }}</span>
      <span>法兰: {{ flangeId }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { colorMapper, type VisualizationMode, type BoltStatusData } from '../utils/colorMapper';

const props = defineProps<{
  flangeId?: string;
  boltData?: BoltStatusData[];
  boltCount?: number;
  flangeParams?: Record<string, any>;
  initialMode?: VisualizationMode;
}>();

const emit = defineEmits<{
  (e: 'bolt-click', bolt: BoltStatusData): void;
  (e: 'mode-change', mode: VisualizationMode): void;
}>();

const containerRef = ref<HTMLDivElement | null>(null);
const canvasRef = ref<HTMLDivElement | null>(null);

const currentMode = ref<VisualizationMode>(props.initialMode || 'status');
const isExploded = ref(false);
const autoRotate = ref(false);
const selectedBolt = ref<BoltStatusData | null>(null);

const flangeId = computed(() => props.flangeId || 'FL001');
const boltCount = computed(() => props.boltCount || 8);

const displayModes = [
  { value: 'status' as const, label: '状态' },
  { value: 'hi' as const, label: 'HI健康度' },
  { value: 'risk' as const, label: '风险' },
];

const statusColors: Record<number, string> = {
  0: '#4CAF50',
  1: '#FFC107',
  2: '#FF9800',
  3: '#F44336',
  4: '#9C27B0',
};

const statusLegend: Record<number, string> = {
  0: '正常',
  1: '关注级预警',
  2: '检查级预警',
  3: '紧急级预警',
  4: '故障',
};

const riskColors: Record<string, string> = {
  low: '#4CAF50',
  medium: '#FFC107',
  high: '#FF5722',
  critical: '#F44336',
};

const riskLegend: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  critical: '极高风险',
};

const hiGradient = 'linear-gradient(to right, #F44336, #FF9800, #FFC107, #8BC34A, #4CAF50)';

let scene: THREE.Scene | null = null;
let camera: THREE.PerspectiveCamera | null = null;
let renderer: THREE.WebGLRenderer | null = null;
let controls: OrbitControls | null = null;
let animationFrameId: number | null = null;
let flangeGroup: THREE.Group | null = null;
let boltMeshes: Map<string, THREE.Mesh> = new Map();
let boltOriginalPositions: Map<string, THREE.Vector3> = new Map();
let raycaster: THREE.Raycaster | null = null;
let mouse: THREE.Vector2 | null = null;

function initScene() {
  if (!canvasRef.value) return;

  const container = canvasRef.value;
  const width = container.clientWidth;
  const height = container.clientHeight;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf5f5f7);

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
  camera.position.set(300, 200, 300);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.minDistance = 100;
  controls.maxDistance = 800;

  raycaster = new THREE.Raycaster();
  mouse = new THREE.Vector2();

  addLights();
  createFlangeModel();
  createGround();

  animate();

  window.addEventListener('resize', onWindowResize);
  renderer.domElement.addEventListener('click', onCanvasClick);
}

function addLights() {
  if (!scene) return;

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
  directionalLight.position.set(200, 300, 200);
  directionalLight.castShadow = true;
  directionalLight.shadow.mapSize.width = 1024;
  directionalLight.shadow.mapSize.height = 1024;
  directionalLight.shadow.camera.near = 0.5;
  directionalLight.shadow.camera.far = 1000;
  directionalLight.shadow.camera.left = -300;
  directionalLight.shadow.camera.right = 300;
  directionalLight.shadow.camera.top = 300;
  directionalLight.shadow.camera.bottom = -300;
  scene.add(directionalLight);

  const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
  fillLight.position.set(-150, 100, -150);
  scene.add(fillLight);
}

function createFlangeModel() {
  if (!scene) return;

  flangeGroup = new THREE.Group();
  scene.add(flangeGroup);

  const outerRadius = props.flangeParams?.flange_outer_radius || 150;
  const innerRadius = props.flangeParams?.flange_inner_radius || 80;
  const thickness = props.flangeParams?.flange_thickness || 30;
  const boltPcdRadius = props.flangeParams?.bolt_pcd_radius || 120;
  const boltRadius = props.flangeParams?.bolt_radius || 10;
  const boltHeight = 25;
  const pipeRadius = props.flangeParams?.pipe_radius || 75;
  const pipeLength = props.flangeParams?.pipe_length || 100;

  const flangeBodyGeo = new THREE.TorusGeometry(
    (outerRadius + innerRadius) / 2,
    (outerRadius - innerRadius) / 2,
    16,
    64
  );
  const flangeMat = new THREE.MeshStandardMaterial({
    color: 0xbfbfc7,
    metalness: 0.3,
    roughness: 0.7,
    side: THREE.DoubleSide,
  });
  const flangeBody = new THREE.Mesh(flangeBodyGeo, flangeMat);
  flangeBody.rotation.x = Math.PI / 2;
  flangeBody.position.y = thickness / 2;
  flangeBody.receiveShadow = true;
  flangeBody.castShadow = true;
  flangeGroup.add(flangeBody);

  const flangeFrontGeo = new THREE.CylinderGeometry(outerRadius, outerRadius, thickness, 64, 1, true);
  const flangeFront = new THREE.Mesh(flangeFrontGeo, flangeMat);
  flangeFront.position.y = thickness / 2;
  flangeFront.receiveShadow = true;
  flangeFront.castShadow = true;
  flangeGroup.add(flangeFront);

  const pipeGeo = new THREE.CylinderGeometry(pipeRadius, pipeRadius, pipeLength, 48, 1, true);
  const pipeMat = new THREE.MeshStandardMaterial({
    color: 0xb3b7bf,
    metalness: 0.4,
    roughness: 0.6,
    side: THREE.DoubleSide,
  });
  const pipe = new THREE.Mesh(pipeGeo, pipeMat);
  pipe.position.y = -pipeLength / 2 + thickness / 2;
  pipe.receiveShadow = true;
  pipe.castShadow = true;
  flangeGroup.add(pipe);

  const boltsGroup = new THREE.Group();
  boltsGroup.name = 'bolts';
  flangeGroup.add(boltsGroup);

  const count = boltCount.value;
  for (let i = 0; i < count; i++) {
    const angle = (2 * Math.PI * i) / count;
    const x = boltPcdRadius * Math.cos(angle);
    const z = boltPcdRadius * Math.sin(angle);

    const boltGroup = new THREE.Group();
    boltGroup.name = `bolt_group_${i}`;
    boltGroup.position.set(x, thickness, z);

    const headHeight = boltHeight * 0.4;
    const shankHeight = boltHeight * 0.6;
    const headRadius = boltRadius * 1.3;

    const headGeo = new THREE.CylinderGeometry(headRadius, headRadius, headHeight, 16);
    const shankGeo = new THREE.CylinderGeometry(boltRadius, boltRadius, shankHeight, 16);

    const boltMat = new THREE.MeshStandardMaterial({
      color: 0x9999a6,
      metalness: 0.5,
      roughness: 0.5,
    });

    const head = new THREE.Mesh(headGeo, boltMat.clone());
    head.position.y = shankHeight / 2 + headHeight / 2;
    head.castShadow = true;
    head.receiveShadow = true;

    const shank = new THREE.Mesh(shankGeo, boltMat.clone());
    shank.position.y = -headHeight / 2;
    shank.castShadow = true;
    shank.receiveShadow = true;

    boltGroup.add(head);
    boltGroup.add(shank);

    const boltId = props.boltData?.[i]?.bolt_id || `B${(i + 1).toString().padStart(3, '0')}`;
    boltGroup.userData.bolt_id = boltId;
    boltGroup.userData.bolt_index = i;

    head.userData.bolt_id = boltId;
    head.userData.bolt_index = i;
    shank.userData.bolt_id = boltId;
    shank.userData.bolt_index = i;

    const boltMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 1, 1), boltMat);
    boltMesh.position.copy(boltGroup.position);
    boltMesh.visible = false;
    boltMesh.userData.bolt_id = boltId;
    boltMesh.userData.bolt_meshes = [head, shank];
    boltMeshes.set(boltId, head);

    boltOriginalPositions.set(boltId, boltGroup.position.clone());

    boltsGroup.add(boltGroup);
  }

  updateBoltColors();
}

function createGround() {
  if (!scene) return;

  const groundGeo = new THREE.PlaneGeometry(800, 800);
  const groundMat = new THREE.MeshStandardMaterial({
    color: 0xe8e8ec,
    metalness: 0,
    roughness: 1,
  });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -50;
  ground.receiveShadow = true;
  scene.add(ground);
}

function updateBoltColors() {
  if (!props.boltData || props.boltData.length === 0) {
    return;
  }

  props.boltData.forEach((bolt, index) => {
    const boltId = bolt.bolt_id;
    const mesh = boltMeshes.get(boltId);
    
    if (mesh && mesh.material) {
      const color = colorMapper.getColor(currentMode.value, bolt);
      const normalizedColor = colorMapper.rgbToNormalized(color);
      
      if (Array.isArray(mesh.material)) {
        mesh.material.forEach((mat) => {
          if (mat instanceof THREE.MeshStandardMaterial) {
            mat.color.setRGB(normalizedColor[0], normalizedColor[1], normalizedColor[2]);
          }
        });
      } else if (mesh.material instanceof THREE.MeshStandardMaterial) {
        mesh.material.color.setRGB(normalizedColor[0], normalizedColor[1], normalizedColor[2]);
      }
    }
  });
}

function animate() {
  animationFrameId = requestAnimationFrame(animate);

  if (controls) {
    controls.autoRotate = autoRotate.value;
    controls.autoRotateSpeed = 2.0;
    controls.update();
  }

  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

function onWindowResize() {
  if (!canvasRef.value || !camera || !renderer) return;

  const width = canvasRef.value.clientWidth;
  const height = canvasRef.value.clientHeight;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
}

function onCanvasClick(event: MouseEvent) {
  if (!canvasRef.value || !raycaster || !mouse || !camera || !scene) return;

  const rect = canvasRef.value.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);

  const boltsGroup = scene.getObjectByName('bolts');
  if (!boltsGroup) return;

  const intersects = raycaster.intersectObjects(boltsGroup.children, true);

  if (intersects.length > 0) {
    const obj = intersects[0].object;
    const boltId = obj.userData.bolt_id;
    
    if (boltId) {
      const boltData = props.boltData?.find((b) => b.bolt_id === boltId);
      if (boltData) {
        selectedBolt.value = boltData;
        emit('bolt-click', boltData);
      }
    }
  } else {
    selectedBolt.value = null;
  }
}

function switchMode(mode: VisualizationMode) {
  currentMode.value = mode;
  updateBoltColors();
  emit('mode-change', mode);
}

function toggleExplosion() {
  isExploded.value = !isExploded.value;
  applyExplosion(isExploded.value ? 1.0 : 0.0);
}

function applyExplosion(factor: number) {
  if (!flangeGroup) return;

  const boltsGroup = flangeGroup.getObjectByName('bolts');
  if (!boltsGroup) return;

  boltsGroup.children.forEach((boltGroup) => {
    const boltId = boltGroup.userData.bolt_id;
    const originalPos = boltOriginalPositions.get(boltId);
    
    if (originalPos) {
      const direction = originalPos.clone().normalize();
      direction.y = 0.3;
      direction.normalize();
      
      const offset = direction.multiplyScalar(40 * factor);
      boltGroup.position.copy(originalPos.clone().add(offset));
    }
  });
}

function toggleAutoRotate() {
  autoRotate.value = !autoRotate.value;
}

function resetView() {
  if (!camera || !controls) return;

  camera.position.set(300, 200, 300);
  controls.reset();
}

watch(() => props.boltData, () => {
  updateBoltColors();
}, { deep: true });

watch(() => currentMode.value, () => {
  updateBoltColors();
});

onMounted(() => {
  initScene();
});

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }

  if (renderer && canvasRef.value) {
    canvasRef.value.removeChild(renderer.domElement);
    renderer.dispose();
  }

  window.removeEventListener('resize', onWindowResize);
});

defineExpose({
  switchMode,
  toggleExplosion,
  toggleAutoRotate,
  resetView,
  applyExplosion,
});
</script>

<style scoped>
.flange-3d-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.viewer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-bottom: 1px solid #e8e8ed;
  flex-shrink: 0;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-label {
  font-size: 13px;
  color: #666;
}

.mode-buttons {
  display: flex;
  gap: 0;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.mode-btn {
  padding: 6px 14px;
  border: none;
  background: white;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
  border-right: 1px solid #dcdfe6;
}

.mode-btn:last-child {
  border-right: none;
}

.mode-btn:hover {
  background: #f5f7fa;
}

.mode-btn.active {
  background: #409eff;
  color: white;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background: white;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: #409eff;
  color: #409eff;
}

.action-btn.active {
  background: #ecf5ff;
  border-color: #409eff;
  color: #409eff;
}

.viewer-canvas {
  flex: 1;
  position: relative;
}

.viewer-canvas :deep(canvas) {
  display: block;
  width: 100% !important;
  height: 100% !important;
}

.viewer-legend {
  position: absolute;
  top: 70px;
  right: 16px;
  background: white;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  min-width: 140px;
}

.legend-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.gradient-bar {
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
}

.gradient-fill {
  width: 100%;
  height: 100%;
}

.gradient-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.viewer-info {
  position: absolute;
  top: 70px;
  left: 16px;
  background: white;
  border-radius: 8px;
  padding: 0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  min-width: 220px;
  overflow: hidden;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #e8e8ed;
}

.info-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.close-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  line-height: 1;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #e8e8ed;
  color: #666;
}

.info-content {
  padding: 12px 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
}

.info-label {
  color: #999;
}

.info-value {
  color: #333;
  font-weight: 500;
}

.hi-value {
  color: #409eff;
}

.viewer-stats {
  position: absolute;
  bottom: 16px;
  left: 16px;
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
  background: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 4px;
}
</style>
