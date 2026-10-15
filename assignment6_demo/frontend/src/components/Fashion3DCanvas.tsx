import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Eye, Layers, Palette, RefreshCw } from 'lucide-react';

interface Fashion3DCanvasProps {
  className?: string;
  showControls?: boolean;
}

export function Fashion3DCanvas({ className = '', showControls = true }: Fashion3DCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [wireframe, setWireframe] = useState(false);
  const [theme, setTheme] = useState<'wine' | 'gold' | 'platinum'>('wine');
  const [autoRotate, setAutoRotate] = useState(true);
  const [activeItem, setActiveItem] = useState<'sneaker' | 'prism' | 'ring'>('prism');

  const [webGLError, setWebGLError] = useState(false);

  const wireframeRef = useRef(wireframe);
  const themeRef = useRef(theme);
  const autoRotateRef = useRef(autoRotate);
  const activeItemRef = useRef(activeItem);

  wireframeRef.current = wireframe;
  themeRef.current = theme;
  autoRotateRef.current = autoRotate;
  activeItemRef.current = activeItem;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let animationFrameId: number;
    const width = container.clientWidth || 600;
    const height = container.clientHeight || 500;

    // Scene
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x1a1618, 0.035);

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 1.2, 5.5);

    // Renderer
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      container.appendChild(renderer.domElement);
    } catch {
      setWebGLError(true);
      return;
    }

    // Group for the entire runway
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);

    // Colors
    const palette = {
      wine: { main: 0x8b263e, accent: 0xd47385, light: 0xff94a8, bg: 0x1f1418 },
      gold: { main: 0xc29b38, accent: 0xe5c365, light: 0xffe6a3, bg: 0x1a1711 },
      platinum: { main: 0x7a8288, accent: 0xb5bcc2, light: 0xe8ecf0, bg: 0x131517 }
    };

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const mainSpot = new THREE.SpotLight(palette.wine.light, 3.5, 20, Math.PI / 4, 0.5, 1);
    mainSpot.position.set(3, 6, 4);
    mainSpot.castShadow = true;
    mainSpot.shadow.mapSize.width = 1024;
    mainSpot.shadow.mapSize.height = 1024;
    scene.add(mainSpot);

    const rimLight = new THREE.PointLight(0x732230, 2.5, 10);
    rimLight.position.set(-4, -1, -2);
    scene.add(rimLight);

    const mouseLight = new THREE.PointLight(0xffffff, 1.2, 8);
    mouseLight.position.set(0, 2, 2);
    scene.add(mouseLight);

    // Runway Platform
    const platformGeo = new THREE.CylinderGeometry(2.4, 2.7, 0.2, 48);
    const platformMat = new THREE.MeshStandardMaterial({
      color: 0x221a1f,
      roughness: 0.25,
      metalness: 0.85,
    });
    const platform = new THREE.Mesh(platformGeo, platformMat);
    platform.position.y = -1.2;
    platform.receiveShadow = true;
    rootGroup.add(platform);

    // Glowing Runway Ring
    const ringGeo = new THREE.TorusGeometry(2.55, 0.035, 16, 64);
    const ringMat = new THREE.MeshStandardMaterial({
      color: palette.wine.accent,
      emissive: palette.wine.main,
      emissiveIntensity: 0.6,
      roughness: 0.1,
      metalness: 0.9,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = -1.1;
    rootGroup.add(ring);

    // Center Stage Pillar
    const pillarGeo = new THREE.CylinderGeometry(1.2, 1.4, 0.35, 32);
    const pillarMat = new THREE.MeshStandardMaterial({
      color: 0x2d2328,
      roughness: 0.3,
      metalness: 0.7,
    });
    const pillar = new THREE.Mesh(pillarGeo, pillarMat);
    pillar.position.y = -0.95;
    rootGroup.add(pillar);

    // Fashion Artifacts (Interchangeable)
    // 1. Multifaceted Haute Couture Diamond / Prism
    const prismGroup = new THREE.Group();
    const prismGeo = new THREE.IcosahedronGeometry(0.95, 0);
    const prismMat = new THREE.MeshPhysicalMaterial({
      color: palette.wine.main,
      roughness: 0.1,
      metalness: 0.2,
      transmission: 0.85,
      ior: 1.7,
      thickness: 1.2,
      clearcoat: 1.0,
      clearcoatRoughness: 0.1,
    });
    const prism = new THREE.Mesh(prismGeo, prismMat);
    prism.castShadow = true;
    prismGroup.add(prism);

    // Inner orbiting rings for the prism
    const orbitRingGeo = new THREE.TorusGeometry(1.35, 0.02, 16, 64);
    const orbitRingMat = new THREE.MeshStandardMaterial({
      color: palette.wine.accent,
      metalness: 0.95,
      roughness: 0.15,
    });
    const orbitRing1 = new THREE.Mesh(orbitRingGeo, orbitRingMat);
    orbitRing1.rotation.x = Math.PI / 3;
    const orbitRing2 = new THREE.Mesh(orbitRingGeo, orbitRingMat);
    orbitRing2.rotation.y = Math.PI / 3;
    prismGroup.add(orbitRing1, orbitRing2);
    prismGroup.position.y = 0.2;
    rootGroup.add(prismGroup);

    // 2. Geometric Sneaker / Shoe Soles Silhouette
    const sneakerGroup = new THREE.Group();
    const soleGeo = new THREE.BoxGeometry(0.85, 0.22, 1.9, 12, 4, 12);
    const soleMat = new THREE.MeshStandardMaterial({
      color: 0xede6e3,
      roughness: 0.35,
      metalness: 0.1,
    });
    const sole = new THREE.Mesh(soleGeo, soleMat);
    sole.position.y = -0.3;
    sole.castShadow = true;
    sneakerGroup.add(sole);

    const upperGeo = new THREE.CylinderGeometry(0.35, 0.42, 1.1, 16);
    const upperMat = new THREE.MeshStandardMaterial({
      color: palette.wine.main,
      roughness: 0.2,
      metalness: 0.5,
    });
    const upper = new THREE.Mesh(upperGeo, upperMat);
    upper.rotation.x = Math.PI / 2.3;
    upper.position.set(0, 0.2, -0.15);
    upper.castShadow = true;
    sneakerGroup.add(upper);

    // Accent swoosh / ribbon
    const ribbonGeo = new THREE.TorusGeometry(0.65, 0.04, 8, 32, Math.PI * 1.2);
    const ribbonMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      metalness: 0.9,
      roughness: 0.1,
    });
    const ribbon = new THREE.Mesh(ribbonGeo, ribbonMat);
    ribbon.position.set(0.2, 0.1, 0.1);
    ribbon.rotation.z = -0.5;
    sneakerGroup.add(ribbon);
    sneakerGroup.position.y = 0.2;
    sneakerGroup.visible = false;
    rootGroup.add(sneakerGroup);

    // 3. Avant-Garde Gyroscope Ring (Luxury Watch/Jewelry Sculpture)
    const gyroGroup = new THREE.Group();
    const gyroRingGeo1 = new THREE.TorusGeometry(1.1, 0.05, 16, 64);
    const gyroRingGeo2 = new THREE.TorusGeometry(0.85, 0.04, 16, 64);
    const gyroRingGeo3 = new THREE.TorusGeometry(0.6, 0.03, 16, 64);
    const gyroMat = new THREE.MeshStandardMaterial({
      color: palette.wine.accent,
      metalness: 0.92,
      roughness: 0.12,
    });
    const gRing1 = new THREE.Mesh(gyroRingGeo1, gyroMat);
    const gRing2 = new THREE.Mesh(gyroRingGeo2, gyroMat);
    const gRing3 = new THREE.Mesh(gyroRingGeo3, gyroMat);
    const coreSphereGeo = new THREE.SphereGeometry(0.28, 32, 32);
    const coreSphereMat = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      emissive: palette.wine.main,
      emissiveIntensity: 0.4,
      metalness: 0.3,
      roughness: 0.1,
    });
    const coreSphere = new THREE.Mesh(coreSphereGeo, coreSphereMat);
    gyroGroup.add(gRing1, gRing2, gRing3, coreSphere);
    gyroGroup.position.y = 0.2;
    gyroGroup.visible = false;
    rootGroup.add(gyroGroup);

    // Ambient floating particles (Stardust / Fashion Dust)
    const particleCount = 120;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 6;
      particlePositions[i + 1] = Math.random() * 3.5 - 1.0;
      particlePositions[i + 2] = (Math.random() - 0.5) * 6;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0xeddfda,
      size: 0.04,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // Mouse tracking for subtle parallax
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      targetX = x * 1.5;
      targetY = -y * 1.0;
    };

    container.addEventListener('mousemove', handleMouseMove);

    // Animation Loop
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth mouse lerp
      mouseX += (targetX - mouseX) * 0.05;
      mouseY += (targetY - mouseY) * 0.05;

      camera.position.x = mouseX * 2.5;
      camera.position.y = 1.2 + mouseY * 1.5;
      camera.lookAt(0, 0.2, 0);

      mouseLight.position.set(mouseX * 4, mouseY * 3 + 2, 2.5);

      // Handle item visibility based on activeItemRef
      const active = activeItemRef.current;
      prismGroup.visible = active === 'prism';
      sneakerGroup.visible = active === 'sneaker';
      gyroGroup.visible = active === 'ring';

      // Update materials from wireframeRef and themeRef
      const currentTheme = palette[themeRef.current];
      const isWire = wireframeRef.current;

      prismMat.wireframe = isWire;
      soleMat.wireframe = isWire;
      upperMat.wireframe = isWire;
      gyroMat.wireframe = isWire;

      mainSpot.color.setHex(currentTheme.light);
      rimLight.color.setHex(currentTheme.main);
      ringMat.emissive.setHex(currentTheme.main);
      ringMat.color.setHex(currentTheme.accent);

      if (prismMat.color) prismMat.color.setHex(currentTheme.main);
      if (upperMat.color) upperMat.color.setHex(currentTheme.main);
      if (gyroMat.color) gyroMat.color.setHex(currentTheme.accent);

      // Rotations and floating motions
      if (autoRotateRef.current) {
        rootGroup.rotation.y = elapsedTime * 0.25;
      }

      // Floating artifact animation
      const floatOffset = Math.sin(elapsedTime * 1.8) * 0.08;

      if (prismGroup.visible) {
        prismGroup.position.y = 0.2 + floatOffset;
        prism.rotation.x = elapsedTime * 0.5;
        prism.rotation.y = elapsedTime * 0.7;
        orbitRing1.rotation.z = elapsedTime * 0.8;
        orbitRing2.rotation.x = elapsedTime * 0.6;
      }

      if (sneakerGroup.visible) {
        sneakerGroup.position.y = 0.2 + floatOffset;
        sneakerGroup.rotation.y = Math.sin(elapsedTime * 0.8) * 0.4 + Math.PI / 4;
        sneakerGroup.rotation.z = Math.cos(elapsedTime * 0.8) * 0.06;
      }

      if (gyroGroup.visible) {
        gyroGroup.position.y = 0.2 + floatOffset;
        gRing1.rotation.x = elapsedTime * 0.9;
        gRing2.rotation.y = elapsedTime * 1.2;
        gRing3.rotation.z = elapsedTime * 1.5;
      }

      // Rotate stardust particles
      particles.rotation.y = -elapsedTime * 0.05;

      renderer.render(scene, camera);
    };

    animate();

    // Resize handler
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('mousemove', handleMouseMove);
      resizeObserver.disconnect();
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
      platformGeo.dispose();
      platformMat.dispose();
      ringGeo.dispose();
      ringMat.dispose();
      pillarGeo.dispose();
      pillarMat.dispose();
      prismGeo.dispose();
      prismMat.dispose();
      orbitRingGeo.dispose();
      orbitRingMat.dispose();
      soleGeo.dispose();
      soleMat.dispose();
      upperGeo.dispose();
      upperMat.dispose();
      ribbonGeo.dispose();
      ribbonMat.dispose();
      gyroRingGeo1.dispose();
      gyroRingGeo2.dispose();
      gyroRingGeo3.dispose();
      gyroMat.dispose();
      coreSphereGeo.dispose();
      coreSphereMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
    };
  }, []);

  return (
    <div className={`fashion-3d-stage ${className}`}>
      <div ref={containerRef} className="canvas-wrapper" style={{ width: '100%', height: '100%', minHeight: '440px', position: 'relative' }}>
        {webGLError && (
          <div className="css-3d-fallback" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '440px', color: '#f5f1ed', textAlign: 'center', padding: '20px' }}>
            <div className="fallback-3d-prism" style={{ width: '120px', height: '120px', margin: '0 auto 20px', border: '2px solid rgba(212,115,133,0.6)', transform: 'rotate(45deg)', animation: 'spin 12s linear infinite', display: 'grid', placeItems: 'center' }}>
              <span style={{ transform: 'rotate(-45deg)', fontSize: '24px', fontWeight: 'bold', color: '#e598a6' }}>3D</span>
            </div>
            <strong style={{ fontSize: '18px', marginBottom: '8px' }}>CORTIS RUNWAY 3D SHOWCASE</strong>
            <p style={{ fontSize: '13px', color: '#b8acb3', maxWidth: '40ch' }}>Trình diễn không gian mẫu vật thời trang 3D tương tác đa chiều</p>
          </div>
        )}
      </div>
      {showControls && (
        <div className="stage-controls" aria-label="Điều khiển hiệu ứng 3D">
          <div className="control-group">
            <span className="control-label"><Eye size={13} aria-hidden="true" /> Vật thể 3D:</span>
            <div className="pill-buttons">
              <button
                type="button"
                className={`pill-btn ${activeItem === 'prism' ? 'active' : ''}`}
                onClick={() => setActiveItem('prism')}
              >
                Khối Haute Couture
              </button>
              <button
                type="button"
                className={`pill-btn ${activeItem === 'sneaker' ? 'active' : ''}`}
                onClick={() => setActiveItem('sneaker')}
              >
                Giày Runway
              </button>
              <button
                type="button"
                className={`pill-btn ${activeItem === 'ring' ? 'active' : ''}`}
                onClick={() => setActiveItem('ring')}
              >
                Trang sức Gyro
              </button>
            </div>
          </div>

          <div className="control-group">
            <span className="control-label"><Palette size={13} aria-hidden="true" /> Ánh sáng:</span>
            <div className="pill-buttons">
              <button
                type="button"
                className={`pill-btn color-btn wine ${theme === 'wine' ? 'active' : ''}`}
                onClick={() => setTheme('wine')}
                title="Đỏ Rượu Vang Cortis"
              >
                Đỏ Rượu
              </button>
              <button
                type="button"
                className={`pill-btn color-btn gold ${theme === 'gold' ? 'active' : ''}`}
                onClick={() => setTheme('gold')}
                title="Vàng Hoàng Gia"
              >
                Ánh Vàng
              </button>
              <button
                type="button"
                className={`pill-btn color-btn plat ${theme === 'platinum' ? 'active' : ''}`}
                onClick={() => setTheme('platinum')}
                title="Bạch Kim Tối Giản"
              >
                Bạch Kim
              </button>
            </div>
          </div>

          <div className="control-group action-group">
            <button
              type="button"
              className={`pill-btn toggle-btn ${wireframe ? 'active' : ''}`}
              onClick={() => setWireframe(v => !v)}
              title="Bật/Tắt chế độ khung lưới 3D"
            >
              <Layers size={13} aria-hidden="true" />
              Khung dây
            </button>
            <button
              type="button"
              className={`pill-btn toggle-btn ${autoRotate ? 'active' : ''}`}
              onClick={() => setAutoRotate(v => !v)}
              title="Bật/Tắt tự động xoay sàn diễn"
            >
              <RefreshCw size={13} aria-hidden="true" className={autoRotate ? 'spin-slow' : ''} />
              {autoRotate ? 'Dừng xoay' : 'Xoay 360°'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
