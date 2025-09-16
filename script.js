
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}
function hexToInt(hex) {
  const h = hex.replace('#','');
  return parseInt(h.length === 3 ? h.split('').map(c => c + c).join('') : h, 16);
}
function shade(hex, percent) { // +brighten / -darken
  const h = hex.replace('#','');
  const num = parseInt(h.length === 3 ? h.split('').map(c => c + c).join('') : h, 16);
  let r = (num >> 16) & 0xff, g = (num >> 8) & 0xff, b = num & 0xff;
  r = Math.min(255, Math.max(0, Math.round(r * (100 + percent) / 100)));
  g = Math.min(255, Math.max(0, Math.round(g * (100 + percent) / 100)));
  b = Math.min(255, Math.max(0, Math.round(b * (100 + percent) / 100)));
  return '#' + (1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1);
}

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('container');

  // --- Theme colors from CSS variables ---
  const COL_BG2 = cssVar('--bg-2', '#0f2940');
  const COL_ACC = cssVar('--accent', '#a82426');
  const COL_MUT = cssVar('--muted', '#f2f2f2');

  // --- Three.js setup ---
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(cssVar('--bg', '#0b233a'));

  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 8, 15);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  container.appendChild(renderer.domElement);

  // Lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.55);
  scene.add(ambientLight);
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.9);
  directionalLight.position.set(5, 10, 5);
  scene.add(directionalLight);

  // Orbit Controls
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.screenSpacePanning = false;
  controls.minDistance = 8;
  controls.maxDistance = 50;
  controls.maxPolarAngle = Math.PI / 2;

  // Pyramid data (bottom -> top)
  const baseBlue = COL_BG2;           // 深蓝主色
  const lightGray = COL_MUT;          // 灰白层
  const accentRed = COL_ACC;          // 顶部强调红

  const pyramidData = [
    { name: 'Local Partner: PICO', color: hexToInt(baseBlue), 
      topRadius: 2.3, bottomRadius: 3.5, height: 1.7, positionY: -1.0 },
    { name: ['Local Manufacturing', 'Local Service', 'Local Application Development'], 
      color: hexToInt(lightGray), 
      topRadius: 1.3, bottomRadius: 2.1, height: 1.5, positionY: 0.8 },
    { name: 'Local Clients: You', color: hexToInt(accentRed), 
      topRadius: 0, bottomRadius: 1.1, height: 1.7, positionY: 2.6 }
  ];

  const layers = [];
  const textLabels = [];
  function createTextSprite(text, color = '#fff', fontSize = 50) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    context.font = `bold ${fontSize}px "Inter", Arial, sans-serif`;
    const textWidth = context.measureText(text).width;
    canvas.width = textWidth + 40;
    canvas.height = fontSize + 40;

    // 背景透明
    context.clearRect(0, 0, canvas.width, canvas.height);

    // 文字
    context.fillStyle = color;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.font = `bold ${fontSize}px "Inter", Arial, sans-serif`;
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(canvas.width / 50, canvas.height / 50, 1);
    return sprite;
  }

  function createPyramidLayers() {
    pyramidData.forEach((data, idx) => {
      const geometry = new THREE.CylinderGeometry(
        data.topRadius, data.bottomRadius, data.height, 3, 1
      );
      const material = new THREE.MeshStandardMaterial({
        color: data.color,
        metalness: 0.35,
        roughness: 0.5,
        emissive: data.color,
        emissiveIntensity: 0.08
      });
      const layer = new THREE.Mesh(geometry, material);
      layer.position.y = data.positionY;
      layer.originalY = data.positionY;
      layer.rotation.y = Math.PI / 3;
      scene.add(layer);
      layers.push(layer);

      // 标签
      if (idx === 0) {
        // 蓝色底层
        const sprite = createTextSprite(data.name, '#fff', 50);
        sprite.position.set(0, data.positionY - data.height / 2 - 0.8, 0);
        scene.add(sprite);
        textLabels.push(sprite);
      } else if (idx === 1) {
        // 灰白层三个面
        const faceLabels = data.name;
        for (let i = 0; i < 3; i++) {
          const angle = i * (2 * Math.PI / 3) + Math.PI / 3;
          const radius = (data.topRadius + data.bottomRadius) / 2;
          const x = Math.cos(angle) * radius;
          const z = Math.sin(angle) * radius;
          const sprite = createTextSprite(faceLabels[i], '#0f2940', 32); // 深蓝色+小号字体
          sprite.position.set(x, data.positionY, z);
          scene.add(sprite);
          textLabels.push(sprite);
        }
      } else if (idx === 2) {
        // 红色顶层
        const sprite = createTextSprite(data.name, '#fff', 50);
        sprite.position.set(0, data.positionY + data.height / 2 + 0.3, 0);
        scene.add(sprite);
        textLabels.push(sprite);
      }
    });
  }

  function addTextLabel(object, text) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    const fontSize = 120;
    context.font = `${fontSize}px Inter, Arial`;
    const textWidth = context.measureText(text).width;
    canvas.width = Math.ceil(textWidth + 40);
    canvas.height = fontSize + 50;

    // Card background
    context.fillStyle = 'rgba(0, 0, 0, 0.55)';
    context.fillRect(0, 0, canvas.width, canvas.height);

    // Text
    context.fillStyle = '#ffffff';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, canvas.width / 2, canvas.height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({ map: texture, depthTest: false });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(canvas.width / 50, canvas.height / 50, 1);
    sprite.position.set(0, object.position.y + 0.05, 0);
    scene.add(sprite);
    textLabels.push(sprite);
  }

  function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }
  window.addEventListener('resize', onWindowResize, false);

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }

  function animateLayersIn() {
    layers.forEach((layer, index) => {
      layer.position.y -= 10;
      gsap.to(layer.position, {
        y: layer.originalY,
        duration: 1.5,
        delay: index * 0.28,
        ease: 'power2.out'
      });
      layer.rotation.y += 0.8;
      gsap.to(layer.rotation, {
        y: Math.PI / 4,
        duration: 1.2,
        delay: index * 0.28 + 0.2,
        ease: 'power2.out'
      });
    });

    textLabels.forEach((label, index) => {
      label.material.opacity = 0;
      gsap.to(label.material, {
        opacity: 1,
        duration: 1.0,
        delay: index * 0.28 + 0.5,
        ease: 'power2.out'
      });
    });
  }

  function showDescriptionBlocks() {
    gsap.set('.description-block', { opacity: 0, x: (i) => i % 2 === 0 ? -50 : 50 });
    gsap.to('.description-block', {
      opacity: 1, x: 0, duration: 0.9, stagger: 0.25, ease: 'power2.out', delay: 0.4
    });
  }

  // Init
  createPyramidLayers();
  animateLayersIn();
  // showDescriptionBlocks();
  animate();
});
