import { NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { ArrowUpRight, Package, Search, Sparkles } from 'lucide-react';
import { useEffect } from 'react';
import { CatalogProvider } from './catalog';
import { SearchProvider } from './state';
import { SearchPage } from './pages/SearchPage';
import { ProductPage } from './pages/ProductPage';
import { OrdersPage } from './pages/OrdersPage';
import { OrderPage } from './pages/OrderPage';
import { CreditsPage } from './pages/CreditsPage';
import { NotFoundPage } from './pages/NotFoundPage';

function Shell() {
  const location = useLocation();
  useEffect(() => {
    if (location.pathname !== '/') window.scrollTo(0, 0);
    document.title = `${location.pathname.startsWith('/orders') ? 'Đơn hàng' : location.pathname.startsWith('/products') ? 'Chi tiết sản phẩm' : location.pathname === '/credits' ? 'Nguồn ảnh' : 'Tìm món đồ đúng với bạn'} · Cortis`;
  }, [location.pathname]);
  return <>
    <a className="skip-link" href="#main-content">Đi đến nội dung</a>
    <header className="site-header"><div className="header-inner">
      <NavLink to="/" className="wordmark" aria-label="Cortis — trang chủ"><span className="brand-symbol" aria-hidden="true"><Sparkles size={25} strokeWidth={1.6} /></span>cortis<span className="brand-dot">.</span></NavLink>
      <nav aria-label="Điều hướng chính"><NavLink to="/" end><Search size={17} aria-hidden="true" /><span>Tìm sản phẩm</span></NavLink><NavLink to="/orders"><Package size={17} aria-hidden="true" /><span>Đơn hàng</span></NavLink><NavLink to="/credits"><span>Nguồn ảnh</span><ArrowUpRight size={16} aria-hidden="true" /></NavLink></nav>
      <span className="demo-label">Dữ liệu minh họa<span>Khách hàng C001</span></span>
    </div></header>
    <main id="main-content" tabIndex={-1}><Routes>
      <Route path="/" element={<SearchPage />} />
      <Route path="/products/:productId" element={<ProductPage />} />
      <Route path="/orders" element={<OrdersPage />} />
      <Route path="/orders/:orderId" element={<OrderPage />} />
      <Route path="/credits" element={<CreditsPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes></main>
    <footer className="site-footer"><div><span className="footer-brand">cortis.</span><p>Khám phá theo cách của bạn.</p></div><p>Giá và tồn kho là dữ liệu minh họa.<br /><NavLink to="/credits">Ảnh thật, nguồn rõ ràng <ArrowUpRight size={13} aria-hidden="true" /></NavLink></p></footer>
  </>;
}
export function App() { return <CatalogProvider><SearchProvider><Shell /></SearchProvider></CatalogProvider>; }
