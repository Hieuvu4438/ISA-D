import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LandingPage } from './LandingPage';

let node: HTMLDivElement;
let root: Root;

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true });
  node = document.createElement('div');
  document.body.append(node);
  root = createRoot(node);

  // Mock HTMLCanvasElement.getContext for WebGL in jsdom
  HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation((contextId: string) => {
    if (contextId === 'webgl' || contextId === 'webgl2' || contextId === 'experimental-webgl') {
      return {
        getExtension: vi.fn(),
        getParameter: vi.fn().mockReturnValue(0),
        createTexture: vi.fn(),
        bindTexture: vi.fn(),
        texParameteri: vi.fn(),
        texImage2D: vi.fn(),
        clearColor: vi.fn(),
        clearDepth: vi.fn(),
        clear: vi.fn(),
        enable: vi.fn(),
        disable: vi.fn(),
        depthFunc: vi.fn(),
        frontFace: vi.fn(),
        cullFace: vi.fn(),
        viewport: vi.fn(),
        createBuffer: vi.fn(),
        bindBuffer: vi.fn(),
        bufferData: vi.fn(),
        createProgram: vi.fn(),
        createShader: vi.fn(),
        shaderSource: vi.fn(),
        compileShader: vi.fn(),
        getShaderParameter: vi.fn().mockReturnValue(true),
        getShaderInfoLog: vi.fn().mockReturnValue(''),
        attachShader: vi.fn(),
        linkProgram: vi.fn(),
        getProgramParameter: vi.fn().mockReturnValue(true),
        getProgramInfoLog: vi.fn().mockReturnValue(''),
        useProgram: vi.fn(),
        getAttribLocation: vi.fn().mockReturnValue(0),
        getUniformLocation: vi.fn().mockReturnValue({}),
        enableVertexAttribArray: vi.fn(),
        vertexAttribPointer: vi.fn(),
        drawArrays: vi.fn(),
        drawElements: vi.fn(),
      };
    }
    return null;
  });

  // Mock ResizeObserver
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

afterEach(async () => {
  await act(async () => root.unmount());
  node.remove();
  vi.unstubAllGlobals();
});

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('LandingPage CORTIS runway and lookbook', () => {
  it('renders CORTIS branding, 5 members, tracks and photo credits', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({
      request_id: 'test-landing',
      products: [
        { product_id: 'P006', name: 'Converse Chuck Taylor', category: 'casual_shoes', brand: 'Converse', color: 'đỏ', price_vnd: 1100000, in_stock: true, image_url: '/api/v1/media/products/P006' }
      ],
      total: 1
    })));

    const router = createMemoryRouter([
      { path: '/landing', element: <LandingPage /> }
    ], { initialEntries: ['/landing'] });

    await act(async () => {
      root.render(<RouterProvider router={router} />);
    });

    // Check title & slogan
    expect(node.textContent).toContain('CORTIS');
    expect(node.textContent).toContain('COLOR OUTSIDE THE LINES');

    // Check all 5 members are present
    expect(node.textContent).toContain('Martin');
    expect(node.textContent).toContain('James (Trịnh Vũ Phàm)');
    expect(node.textContent).toContain('Juhoon (Kim Joo-hoon)');
    expect(node.textContent).toContain('Seonghyeon (Eom Sung-hyun)');
    expect(node.textContent).toContain('Keonho (Ahn Gan-ho)');

    // Check tracks are present
    expect(node.textContent).toContain('What You Want');
    expect(node.textContent).toContain('FaSHioN');

    // Check award and credits
    expect(node.textContent).toContain('ROOKIE ARTIST OF THE YEAR');
    expect(node.textContent).toContain('TikTok Awards Korea');
    expect(node.textContent).toContain('Wikimedia Commons');
  });
});
