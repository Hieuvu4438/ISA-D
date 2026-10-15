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
import { AccountPage } from './pages/AccountPage';
import { BrowsePage } from './pages/BrowsePage';
import { CartPage, WishlistPage } from './pages/ShoppingPages';
import { CheckoutPage, PurchaseHistoryPage } from './pages/CheckoutPage';
import { AdminPage } from './pages/AdminPage';
import { AdminReturnsPage } from './pages/AdminReturnsPage';

import { LandingPage } from './pages/LandingPage';

function Shell() {
  const location = useLocation();
  useEffect(() => {
    if (location.pathname !== '/') window.scrollTo(0, 0);
    document.title = `${location.pathname === '/landing' ? 'CORTIS 2026 Runway 3D & Lookbook' : location.pathname.startsWith('/admin') ? 'Quản trị' : location.pathname === '/checkout' ? 'Xác nhận đặt hàng' : location.pathname === '/purchases' ? 'Đơn đã đặt' : location.pathname === '/cart' ? 'Giỏ hàng' : location.pathname === '/wishlist' ? 'Món đồ đã lưu' : location.pathname === '/account' ? 'Tài khoản' : location.pathname === '/catalog' ? 'Bộ sưu tập' : location.pathname.startsWith('/orders') ? 'Đơn hàng' : location.pathname.startsWith('/products') ? 'Chi tiết sản phẩm' : location.pathname === '/credits' ? 'Nguồn ảnh' : 'Tìm món đồ đúng với bạn'} · Cortis`;
  }, [location.pathname]);
  return <>
    <a className="skip-link" href="#main-content">Đi đến nội dung</a>
    <header className="site-header"><div className="header-inner">
      <NavLink to="/" className="wordmark" aria-label="Cortis — trang chủ"><span className="brand-symbol" aria-hidden="true"><Sparkles size={25} strokeWidth={1.6} /></span>cortis<span className="brand-dot">.</span></NavLink>
      <nav aria-label="Điều hướng chính">
        <NavLink to="/landing" className="nav-runway-badge"><Sparkles size={16} aria-hidden="true" /><span>Runway 3D & Lookbook</span></NavLink>
        <NavLink to="/catalog">Bộ sưu tập</NavLink>
        <NavLink to="/" end><Search size={17} aria-hidden="true" /><span>Tìm sản phẩm</span></NavLink>
        <NavLink to="/orders"><Package size={17} aria-hidden="true" /><span>Đơn hàng</span></NavLink>
        <NavLink to="/credits"><span>Nguồn ảnh</span><ArrowUpRight size={16} aria-hidden="true" /></NavLink>
      </nav>
      <div className="header-shopping"><NavLink className="text-link" to="/wishlist">Yêu thích</NavLink><NavLink className="text-link" to="/cart">Giỏ hàng</NavLink><NavLink className="text-link" to="/account">Tài khoản</NavLink></div>
    </div></header>
    <main id="main-content" tabIndex={-1}><Routes>
      <Route path="/" element={<SearchPage />} />
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/products/:productId" element={<ProductPage />} />
      <Route path="/orders" element={<OrdersPage />} />
      <Route path="/orders/:orderId" element={<OrderPage />} />
      <Route path="/credits" element={<CreditsPage />} />
      <Route path="/account" element={<AccountPage />} />
      <Route path="/catalog" element={<BrowsePage />} />
      <Route path="/cart" element={<CartPage />} />
      <Route path="/wishlist" element={<WishlistPage />} />
      <Route path="/checkout" element={<CheckoutPage />} />
      <Route path="/purchases" element={<PurchaseHistoryPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="/admin/returns" element={<AdminReturnsPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes></main>
    <footer className="site-footer">
      <div className="footer-columns">
        <div className="footer-col brand-col">
          <span className="footer-brand">cortis<span className="brand-dot">.</span></span>
          <p className="footer-tagline">Color Outside The Lines · Thời trang vượt qua mọi đường kẻ khuôn khổ.</p>
          <p className="footer-subtext">Lấy cảm hứng từ năng lượng sáng tạo của nhóm nhạc CORTIS và nghệ thuật chế tác tối giản hiện đại.</p>
        </div>
        <div className="footer-col">
          <h4>Khám phá</h4>
          <ul>
            <li><NavLink to="/landing">Runway 3D & Lookbook</NavLink></li>
            <li><NavLink to="/catalog">Bộ sưu tập đầy đủ</NavLink></li>
            <li><NavLink to="/">Tìm kiếm AI Đa phương thức</NavLink></li>
            <li><NavLink to="/wishlist">Món đồ yêu thích</NavLink></li>
            <li><NavLink to="/cart">Giỏ hàng</NavLink></li>
          </ul>
        </div>
        <div className="footer-col">
          <h4>Dịch vụ & Đơn hàng</h4>
          <ul>
            <li><NavLink to="/orders">Tra cứu đơn hàng</NavLink></li>
            <li><NavLink to="/purchases">Lịch sử mua sắm</NavLink></li>
            <li><NavLink to="/account">Tài khoản cá nhân</NavLink></li>
            <li><NavLink to="/admin">Cổng quản trị showroom</NavLink></li>
            <li><NavLink to="/admin/returns">Yêu cầu hoàn trả</NavLink></li>
          </ul>
        </div>
        <div className="footer-col">
          <h4>Minh bạch & Bản quyền</h4>
          <p className="footer-notice">100% hình ảnh sản phẩm và nhóm nhạc CORTIS là ảnh thật được cấp phép từ Wikimedia Commons và các đối tác.</p>
          <NavLink to="/credits" className="footer-credit-link">Xem bảng nguồn ảnh & giấy phép <ArrowUpRight size={14} aria-hidden="true" /></NavLink>
        </div>
      </div>
      <div className="footer-bottom">
        <p>© 2026 Cortis Storefront. Dữ liệu giá và tồn kho mang tính chất minh họa phục vụ demo hệ thống AI.</p>
        <div className="footer-badges">
          <span>CLIP 512D</span>
          <span>Azure Speech / Whisper</span>
          <span>FastAPI + React 19</span>
        </div>
      </div>
    </footer>
  </>;
}
export function App() { return <CatalogProvider><SearchProvider><Shell /></SearchProvider></CatalogProvider>; }
