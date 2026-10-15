import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  ArrowUpRight,
  AudioLines,
  Camera,
  Check,
  Disc,
  ExternalLink,
  Flame,
  Music2,
  PackageCheck,
  Search,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react';
import { Fashion3DCanvas } from '../components/Fashion3DCanvas';
import { use3DTilt } from '../lib/use3DTilt';
import { formatMoney, categoryLabels, ProductImage } from '../ui';
import type { ProductSummary } from '../lib/types';
import { getProducts } from '../lib/api';

interface CortisMember {
  id: string;
  name: string;
  role: string;
  image: string;
  bio: string;
  styleConcept: string;
  recommendedProductId: string;
  recommendedProductName: string;
  sourceCredit: string;
  license: string;
  sourceUrl: string;
}

const CORTIS_MEMBERS: CortisMember[] = [
  {
    id: 'martin',
    name: 'Martin',
    role: 'Leader & Vocalist',
    image: '/images/cortis/cortis_martin.jpg',
    bio: 'Trưởng nhóm định hình tư duy sáng tạo tự do cho CORTIS. Phong cách kết hợp giữa cấu trúc blazer sắc bén và sự nổi loạn của streetwear Seoul.',
    styleConcept: 'Architectural Tailoring & High-top Sneakers',
    recommendedProductId: 'P006',
    recommendedProductName: 'Converse Chuck Taylor All Star đỏ cổ cao',
    sourceCredit: 'Wikimedia Commons contributors',
    license: 'CC BY 3.0',
    sourceUrl: 'https://commons.wikimedia.org/wiki/File:Cortis_Martin_at_TikTok_Awards_Korea.jpg',
  },
  {
    id: 'james',
    name: 'James (Trịnh Vũ Phàm)',
    role: 'Main Dancer & Rapper',
    image: '/images/cortis/cortis_james.png',
    bio: 'Vũ công chính với năng lượng sân khấu bùng nổ. Thời trang sân bay của James nổi bật với phom dáng oversize phóng khoáng và túi đeo chéo cá tính.',
    styleConcept: 'Airport Dynamic & Athletic Avant-garde',
    recommendedProductId: 'P011',
    recommendedProductName: 'Túi da màu nâu dây đeo chéo',
    sourceCredit: 'Newsen / Wikimedia Commons',
    license: 'CC BY 3.0',
    sourceUrl: 'https://commons.wikimedia.org/wiki/File:JAMES_of_CORTIS_at_Airport_in_20251001.png',
  },
  {
    id: 'juhoon',
    name: 'Juhoon (Kim Joo-hoon)',
    role: 'Creator & Visual',
    image: '/images/cortis/cortis_juhoon.png',
    bio: 'Gương mặt đại diện mang nét đẹp thanh tao, tinh tế. Phong cách ưa chuộng bảng màu trung tính, đỏ rượu burgundy và chất liệu len dệt cao cấp.',
    styleConcept: 'Minimalist Casual Luxury & Clean Lines',
    recommendedProductId: 'P007',
    recommendedProductName: 'Nike Air Force 1 trắng cổ điển',
    sourceCredit: 'SBS Radio / Wikimedia Commons',
    license: 'CC BY 3.0',
    sourceUrl: 'https://commons.wikimedia.org/wiki/File:JUHOON_of_CORTIS_at_Cultwo_Show_in_20250914.png',
  },
  {
    id: 'seonghyeon',
    name: 'Seonghyeon (Eom Sung-hyun)',
    role: 'Creator & Performer',
    image: '/images/cortis/cortis_seonghyeon.png',
    bio: 'Nghệ sĩ trình diễn với gu thẩm mỹ tiên phong. Chuyên gia phối layer nhiều lớp màu sắc đối lập cùng giày địa hình độc đáo.',
    styleConcept: 'Layered Avant-Garde & Trail Hybrid',
    recommendedProductId: 'P003',
    recommendedProductName: 'Giày Asics Gel chạy bộ địa hình xanh đậm',
    sourceCredit: 'SBS Radio / Wikimedia Commons',
    license: 'CC BY 3.0',
    sourceUrl: 'https://commons.wikimedia.org/wiki/File:SEONGHYEON_of_CORTIS_at_Cultwo_Show_in_20250914.png',
  },
  {
    id: 'keonho',
    name: 'Keonho (Ahn Gan-ho)',
    role: 'Vocalist',
    image: '/images/cortis/cortis_keonho.jpg',
    bio: 'Giọng ca truyền cảm hứng của CORTIS. Phong cách thời trang nhấn mạnh vào phụ kiện kim loại, đồng hồ cơ và sneaker đế thô cá tính.',
    styleConcept: 'Urban Edge & Statement Footwear',
    recommendedProductId: 'P001',
    recommendedProductName: 'Giày chạy bộ On Cloudmonster màu đen',
    sourceCredit: 'Wikimedia Commons contributors',
    license: 'CC BY 3.0',
    sourceUrl: 'https://commons.wikimedia.org/wiki/File:Cortis_Keonho_at_TikTok_Awards_Korea.jpg',
  },
];

const TRACKS = [
  {
    num: '01',
    title: 'What You Want',
    tag: 'Debut Digital Single',
    vibe: 'Hip-hop / High-energy Street Beat',
    duration: '3:18',
  },
  {
    num: '02',
    title: 'FaSHioN',
    tag: 'Runway Anthem',
    vibe: 'Avant-garde Fashion Synth / Runway Bass',
    duration: '2:54',
  },
  {
    num: '03',
    title: 'Color Outside The Lines',
    tag: '1st EP Title Track',
    vibe: 'Billboard 200 Charted / Freedom Sound',
    duration: '3:42',
  },
];

function MemberCard({ member }: { member: CortisMember }) {
  const { ref, onMouseMove, onMouseLeave } = use3DTilt<HTMLDivElement>({
    maxTilt: 10,
    scale: 1.03,
    perspective: 800,
  });

  return (
    <article
      ref={ref}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      className="member-card tilt-card"
    >
      <div className="member-image-frame">
        <img
          src={member.image}
          alt={`Thành viên ${member.name} - ${member.role}`}
          className="member-photo"
          loading="lazy"
        />
        <div className="member-role-badge">
          <span>{member.role}</span>
        </div>
        <div className="glare-effect" />
      </div>

      <div className="member-info">
        <div className="member-header">
          <h3>{member.name}</h3>
          <span className="concept-pill">{member.styleConcept}</span>
        </div>
        <p className="member-bio">{member.bio}</p>

        <div className="member-recommendation">
          <span className="recommend-label">
            <Sparkles size={13} aria-hidden="true" /> Phối đồ phong cách {member.name}:
          </span>
          <Link
            to={`/products/${member.recommendedProductId}`}
            className="recommend-link"
          >
            <span>{member.recommendedProductName}</span>
            <ArrowUpRight size={15} aria-hidden="true" />
          </Link>
        </div>

        <div className="member-credit">
          <small>
            Ảnh: {member.sourceCredit} ({member.license}) ·{' '}
            <a
              href={member.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-link"
            >
              Nguồn gốc
            </a>
          </small>
        </div>
      </div>
    </article>
  );
}

export function LandingPage() {
  const [featuredProducts, setFeaturedProducts] = useState<ProductSummary[]>([]);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [vipEmail, setVipEmail] = useState('');
  const [vipSuccess, setVipSuccess] = useState(false);
  const [activeTrack, setActiveTrack] = useState(1);

  const heroTilt = use3DTilt<HTMLDivElement>({ maxTilt: 6, scale: 1.015 });
  const gdaTilt = use3DTilt<HTMLDivElement>({ maxTilt: 6, scale: 1.015 });

  useEffect(() => {
    const controller = new AbortController();
    getProducts(0, 8, controller.signal)
      .then(res => {
        if (!controller.signal.aborted) {
          setFeaturedProducts(res.products);
          setLoadingProducts(false);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setLoadingProducts(false);
      });
    return () => controller.abort();
  }, []);

  const handleVipSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!vipEmail.trim() || !vipEmail.includes('@')) return;
    setVipSuccess(true);
  };

  return (
    <div className="landing-fashion-page">
      {/* 1. Ticker announcement */}
      <div className="campaign-ticker" role="region" aria-label="Thông báo chiến dịch">
        <div className="ticker-track">
          <span className="ticker-item">
            <Flame size={14} className="ticker-icon" aria-hidden="true" />
            <strong>CORTIS 2026 RUNWAY EDITION</strong> · COLOR OUTSIDE THE LINES
          </span>
          <span className="ticker-dot">✦</span>
          <span className="ticker-item">
            BỘ SƯU TẬP THỜI TRANG ĐƯỜNG PHỐ & SÀN DIỄN CAO CẤP HỢP TÁC CÙNG BIGHIT CREATOR CREW
          </span>
          <span className="ticker-dot">✦</span>
          <span className="ticker-item">
            <Zap size={14} className="ticker-icon" aria-hidden="true" />
            TRẢI NGHIỆM TÌM KIẾM AI ĐA PHƯƠNG THỨC 512D BẰNG TIẾNG VIỆT & HÌNH ẢNH
          </span>
          <span className="ticker-dot">✦</span>
          <span className="ticker-item">
            MIỄN PHÍ GIAO HÀNG TOÀN QUỐC CHO ĐƠN TỪ 1.000.000₫
          </span>
          <span className="ticker-dot">✦</span>
          <span className="ticker-item">
            <Flame size={14} className="ticker-icon" aria-hidden="true" />
            <strong>CORTIS 2026 RUNWAY EDITION</strong> · COLOR OUTSIDE THE LINES
          </span>
        </div>
      </div>

      {/* 2. Hero Section with 3D Canvas */}
      <section className="landing-hero" aria-labelledby="landing-hero-heading">
        <div className="landing-hero-grid">
          <div className="landing-hero-content">
            <div className="hero-eyebrow">
              <span className="pill-badge">BIGHIT MUSIC // 2026 FASHION LAUNCH</span>
              <span className="pill-badge accent">CLIP 512D AI POWERED</span>
            </div>

            <h1 id="landing-hero-heading" className="landing-title">
              CORTIS<span className="accent-dot">.</span>
              <span className="landing-title-sub">COLOR OUTSIDE THE LINES</span>
            </h1>

            <p className="landing-lead">
              Nơi tư duy sáng tạo tự do của nhóm nhạc tân binh <strong>CORTIS</strong> giao thoa
              cùng nghệ thuật chế tác thời trang tối giản. Mọi phom dáng, chất liệu và đường cắt
              được tinh tuyển để vượt qua khuôn mẫu thông thường — khám phá thế giới thời trang
              bằng mô tả tiếng Việt, giọng nói hoặc một bức ảnh thật.
            </p>

            <div className="hero-actions">
              <a href="#lookbook-section" className="primary-button hero-cta-btn">
                <span>Khám phá Lookbook CORTIS</span>
                <ArrowRight size={18} aria-hidden="true" />
              </a>
              <Link to="/" className="secondary-button hero-cta-secondary">
                <Search size={17} aria-hidden="true" />
                <span>Tìm kiếm bằng AI</span>
              </Link>
              <Link to="/catalog" className="text-link hero-cta-link">
                <span>Xem trọn bộ sưu tập</span>
                <ArrowUpRight size={16} aria-hidden="true" />
              </Link>
            </div>

            {/* Quick Stats Highlights */}
            <div className="hero-metrics">
              <div className="metric-box">
                <span className="metric-val">512D</span>
                <span className="metric-lbl">Vector Không Gian AI</span>
              </div>
              <div className="metric-divider" />
              <div className="metric-box">
                <span className="metric-val">100%</span>
                <span className="metric-lbl">Ảnh Chụp Thực Tế</span>
              </div>
              <div className="metric-divider" />
              <div className="metric-box">
                <span className="metric-val">05</span>
                <span className="metric-lbl">Thành Viên CORTIS</span>
              </div>
              <div className="metric-divider" />
              <div className="metric-box">
                <span className="metric-val">vi-VN</span>
                <span className="metric-lbl">Ngôn Ngữ Tối Ưu</span>
              </div>
            </div>
          </div>

          {/* 3D Runway Stage Canvas */}
          <div className="landing-hero-3d">
            <div className="canvas-frame">
              <div className="canvas-header-bar">
                <div className="dots">
                  <span className="dot red" />
                  <span className="dot yellow" />
                  <span className="dot green" />
                </div>
                <span className="stage-title">SÀN DIỄN 3D TƯƠNG TÁC · CORTIS RUNWAY</span>
                <span className="fps-indicator">WebGL 60 FPS</span>
              </div>
              <Fashion3DCanvas />
              <div className="canvas-footer-hint">
                <span>✦ Di chuyển chuột để xoay góc nhìn 3D · Bấm vật thể để đổi mẫu vật</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. The CORTIS Group Story & Golden Disc Awards Section */}
      <section className="cortis-story-section" aria-labelledby="cortis-story-title">
        <div className="section-container">
          <div className="story-grid">
            <div
              ref={heroTilt.ref}
              onMouseMove={heroTilt.onMouseMove}
              onMouseLeave={heroTilt.onMouseLeave}
              className="story-visual-card tilt-card"
            >
              <img
                src="/images/cortis/cortis_group_tiktok.jpg"
                alt="Đội hình 5 thành viên CORTIS tại TikTok Awards Korea"
                className="story-main-photo"
                loading="lazy"
              />
              <div className="visual-overlay">
                <span className="visual-tag">CORTIS at TikTok Awards Korea (2025)</span>
                <p className="visual-caption">Từ trái sang phải: James, Seonghyeon, Juhoon, Keonho, Martin</p>
                <small className="visual-credit">Ảnh: TikTok Awards Korea / Wikimedia Commons (CC BY 3.0)</small>
              </div>
              <div className="glare-effect" />
            </div>

            <div className="story-copy">
              <div className="story-eyebrow">
                <Sparkles size={16} aria-hidden="true" />
                <span>TƯ DUY SÁNG TẠO ĐỘT PHÁ</span>
              </div>
              <h2 id="cortis-story-title" className="section-title">
                "Color Outside The Lines" — Phá Vỡ Mọi Đường Kẻ Khuôn Khổ
              </h2>
              <p className="story-paragraph">
                <strong>CORTIS (코르티스)</strong> là nhóm nhạc nam trực thuộc <strong>BigHit Music</strong>,
                ra mắt vào tháng 8 năm 2025 gồm 5 thành viên tài năng: <strong>Martin, James, Juhoon, Seonghyeon, và Keonho</strong>.
                Tên gọi CORTIS bắt nguồn từ triết lý <em>"Color Outside The Lines"</em> — khuyến khích tư duy tự do,
                vượt lên các tiêu chuẩn áp đặt để kiến tạo phong cách riêng biệt.
              </p>
              <p className="story-paragraph">
                Không chỉ tự tay sản xuất âm nhạc và vũ đạo, CORTIS còn định hình ngôn ngữ thời trang
                đương đại: sự dung hòa giữa phom dáng may đo thanh lịch (tailored) và tinh thần đường phố (streetwear) năng động.
                Showroom Cortis tự hào là điểm chạm nơi người yêu thời trang có thể trải nghiệm trang phục lấy cảm hứng
                từ tinh thần tự do này.
              </p>

              {/* Music & Runway Connection */}
              <div className="soundtrack-box">
                <div className="soundtrack-header">
                  <Disc size={18} className="spin-slow" aria-hidden="true" />
                  <strong>CORTIS OFFICIAL SOUNDTRACK // RUNWAY PLAYLIST</strong>
                </div>
                <div className="track-list">
                  {TRACKS.map((track, idx) => (
                    <div
                      key={track.num}
                      className={`track-item ${activeTrack === idx ? 'is-playing' : ''}`}
                      onClick={() => setActiveTrack(idx)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={e => { if (e.key === 'Enter') setActiveTrack(idx); }}
                    >
                      <div className="track-left">
                        <Music2 size={16} aria-hidden="true" />
                        <div>
                          <strong>{track.num}. {track.title}</strong>
                          <span className="track-tag">{track.tag}</span>
                        </div>
                      </div>
                      <div className="track-right">
                        <span className="track-vibe">{track.vibe}</span>
                        <span className="track-time">{track.duration}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Golden Disc Awards Recognition Banner */}
          <div
            ref={gdaTilt.ref}
            onMouseMove={gdaTilt.onMouseMove}
            onMouseLeave={gdaTilt.onMouseLeave}
            className="award-banner tilt-card"
          >
            <div className="award-image-col">
              <img
                src="/images/cortis/cortis_group_gda.jpg"
                alt="CORTIS tại lễ trao giải Golden Disc Awards lần thứ 40"
                className="award-photo"
                loading="lazy"
              />
            </div>
            <div className="award-copy-col">
              <span className="award-ribbon">🏆 ROOKIE ARTIST OF THE YEAR</span>
              <h3>Chiến Thắng Tân Binh Xuất Sắc Nhất Năm 2026</h3>
              <p>
                Tại lễ trao giải Golden Disc Awards lần thứ 40 (2026), CORTIS đã được vinh danh là Tân binh của năm,
                khẳng định sức ảnh hưởng vượt bậc của nhóm trong cả lĩnh vực âm nhạc và định hình xu hướng thời trang trẻ toàn cầu.
              </p>
              <div className="award-meta-row">
                <span className="award-meta">
                  <ShieldCheck size={16} aria-hidden="true" />
                  Ảnh bản quyền Wikimedia Commons (CC BY-SA 4.0)
                </span>
                <a
                  href="https://commons.wikimedia.org/wiki/File:Cortis_at_40th_Golden_Disc_Awards,_2026.jpg"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="award-source-link"
                >
                  <span>Xem hồ sơ lưu trữ</span>
                  <ExternalLink size={14} aria-hidden="true" />
                </a>
              </div>
            </div>
            <div className="glare-effect" />
          </div>
        </div>
      </section>

      {/* 4. The 5 Members Lookbook Section */}
      <section id="lookbook-section" className="lookbook-section" aria-labelledby="lookbook-title">
        <div className="section-container">
          <div className="section-header center">
            <span className="section-kicker">EDITORIAL LOOKBOOK 2026</span>
            <h2 id="lookbook-title" className="section-title">
              Phong Cách Cá Tính Từ 5 Thành Viên CORTIS
            </h2>
            <p className="section-subtitle">
              Mỗi thành viên là một mảnh ghép phong cách độc bản. Khám phá và phối đồ theo phong thái của Martin, James, Juhoon, Seonghyeon và Keonho.
            </p>
          </div>

          <div className="members-grid">
            {CORTIS_MEMBERS.map(member => (
              <MemberCard key={member.id} member={member} />
            ))}
          </div>
        </div>
      </section>

      {/* 5. Interactive AI Search Spotlight Banner */}
      <section className="search-spotlight-section" aria-labelledby="ai-search-spotlight-title">
        <div className="section-container">
          <div className="spotlight-card">
            <div className="spotlight-content">
              <span className="spotlight-tag">
                <Zap size={14} aria-hidden="true" /> ĐỘT PHÁ CÔNG NGHỆ TÌM KIẾM
              </span>
              <h2 id="ai-search-spotlight-title">
                Tìm Bằng Mô Tả Tự Nhiên, Giọng Nói & Tải Ảnh Thật
              </h2>
              <p>
                Không còn phải gõ đúng từ khóa máy móc. Bạn có thể tìm kiếm như đang trò chuyện:
                <em>“Giày Converse đỏ cổ cao của Martin”</em>, <em>“Túi da màu nâu phong cách James”</em>,
                hoặc thả một tấm ảnh thời trang chụp trên phố để AI đối chiếu trong không gian 512 chiều.
              </p>

              <div className="spotlight-modes-list">
                <div className="mode-pill">
                  <Search size={16} aria-hidden="true" />
                  <span>Mô tả tiếng Việt</span>
                </div>
                <div className="mode-pill">
                  <AudioLines size={16} aria-hidden="true" />
                  <span>Giọng nói STT</span>
                </div>
                <div className="mode-pill">
                  <Camera size={16} aria-hidden="true" />
                  <span>Tìm bằng ảnh</span>
                </div>
                <div className="mode-pill">
                  <Sparkles size={16} aria-hidden="true" />
                  <span>Mô tả + Ảnh kết hợp</span>
                </div>
              </div>

              <div className="spotlight-action">
                <Link to="/" className="primary-button">
                  <span>Trải nghiệm AI Search ngay</span>
                  <ArrowRight size={18} aria-hidden="true" />
                </Link>
                <Link to="/catalog" className="secondary-button light">
                  <span>Duyệt bộ sưu tập thủ công</span>
                </Link>
              </div>
            </div>

            <div className="spotlight-visual">
              <div className="vector-radar-card">
                <div className="radar-header">
                  <span>CLIP MULTIMODAL 512D RADAR</span>
                  <span className="live-status">LIVE AI PIPELINE</span>
                </div>
                <div className="radar-circle">
                  <div className="radar-sweep" />
                  <div className="radar-point p1" title="P006 - Converse Đỏ" />
                  <div className="radar-point p2" title="P001 - On Cloud Đen" />
                  <div className="radar-point p3" title="P011 - Túi Da Nâu" />
                  <div className="radar-point p4" title="P007 - Air Force Trắng" />
                  <div className="radar-point p5" title="P012 - Hermès Kelly Đỏ" />
                </div>
                <div className="radar-legend">
                  <span>Cosine Similarity Vector Embedding</span>
                  <small>Định vị tức thì trên toàn bộ catalog</small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Curated Runway Products Grid */}
      <section className="runway-picks-section" aria-labelledby="runway-picks-title">
        <div className="section-container">
          <div className="section-header between">
            <div>
              <span className="section-kicker">CURATED SELECTION</span>
              <h2 id="runway-picks-title" className="section-title">
                Sản Phẩm Tiêu Biểu Trong Bộ Sưu Tập
              </h2>
              <p className="section-subtitle">
                Những mẫu giày, túi và phụ kiện thật được tuyển chọn kỹ lưỡng cho showroom Cortis.
              </p>
            </div>
            <Link to="/catalog" className="text-link view-all-btn">
              <span>Xem tất cả sản phẩm</span>
              <ArrowRight size={17} aria-hidden="true" />
            </Link>
          </div>

          {loadingProducts ? (
            <div className="product-grid skeleton-grid">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="product-skeleton">
                  <div />
                  <span />
                  <span />
                </div>
              ))}
            </div>
          ) : (
            <div className="product-grid">
              {featuredProducts.slice(0, 4).map(prod => (
                <article key={prod.product_id} className="product-card tilt-card" data-testid="product-card">
                  <Link to={`/products/${prod.product_id}`} className="product-card-link">
                    <div className="product-card-media">
                      <ProductImage src={prod.image_url} alt={prod.name} retry={false} />
                      {!prod.in_stock && <span className="stock-tag">Tạm hết hàng</span>}
                      {prod.in_stock && (
                        <span className="runway-tag">
                          <Check size={12} aria-hidden="true" /> Còn hàng
                        </span>
                      )}
                      <span className="product-open" aria-hidden="true">
                        <ArrowUpRight size={20} />
                      </span>
                      <div className="glare-effect" />
                    </div>
                    <div className="product-card-copy">
                      <div className="product-brand">
                        {prod.brand}
                        <span>{categoryLabels[prod.category]}</span>
                      </div>
                      <h3>{prod.name}</h3>
                      <p className="product-color">{prod.color}</p>
                      <div className="product-price-row">
                        <strong>{formatMoney(prod.price_vnd)}</strong>
                      </div>
                    </div>
                  </Link>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* 7. Brand Commitments & Atelier Philosophy */}
      <section className="atelier-philosophy-section" aria-labelledby="philosophy-title">
        <div className="section-container">
          <div className="philosophy-card">
            <div className="philosophy-header">
              <span className="pill-badge">CAM KẾT CHẤT LƯỢNG THẬT</span>
              <h2 id="philosophy-title">Triết Lý Showroom Mẫu Vật Thực Tế</h2>
            </div>

            <div className="philosophy-grid">
              <div className="philosophy-item">
                <div className="item-icon-box">
                  <PackageCheck size={24} aria-hidden="true" />
                </div>
                <h3>100% Ảnh Chụp Thật Từ Mạng</h3>
                <p>
                  Mọi sản phẩm trong catalog đều là ảnh chụp thật do các nhiếp ảnh gia và tổ chức cấp phép mở
                  (Wikimedia Commons, bảo tàng, thương hiệu). Chúng tôi nói không với ảnh AI tổng hợp hay render 3D giả lập cho sản phẩm.
                </p>
                <Link to="/credits" className="text-link">
                  <span>Xem chi tiết nguồn ảnh</span>
                  <ArrowUpRight size={14} aria-hidden="true" />
                </Link>
              </div>

              <div className="philosophy-item">
                <div className="item-icon-box">
                  <Zap size={24} aria-hidden="true" />
                </div>
                <h3>Xử Lý Toàn Diện Trên CPU Local</h3>
                <p>
                  Hệ thống AI chạy ổn định trên CPU với mô hình CLIP 512 chiều tối ưu hóa tiếng Việt,
                  sẵn sàng hoạt động độc lập ngay cả khi không có kết nối dịch vụ đám mây.
                </p>
              </div>

              <div className="philosophy-item">
                <div className="item-icon-box">
                  <ShieldCheck size={24} aria-hidden="true" />
                </div>
                <h3>Bảo Mật Quyền Riêng Tư & Dữ Liệu</h3>
                <p>
                  Dữ liệu khách hàng và bản ghi âm giọng nói được bảo vệ nghiêm ngặt.
                  Giọng nói chỉ xử lý tạm thời để nhận dạng transcript và không lưu trữ trái phép.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 8. VIP Club / Newsletter Subscription Form */}
      <section className="vip-newsletter-section" aria-labelledby="vip-title">
        <div className="section-container">
          <div className="vip-box">
            <div className="vip-content">
              <span className="vip-badge">CORTIS VIP CLUB // ƯU ĐÃI ĐẶC QUYỀN</span>
              <h2 id="vip-title">Gia Nhập Cộng Đồng CORTIS Insider</h2>
              <p>
                Đăng ký để nhận sớm thông tin về các đợt phát hành Runway giới hạn,
                lookbook độc quyền và mã ưu đãi giảm 15% cho đơn hàng đầu tiên.
              </p>

              {vipSuccess ? (
                <div className="vip-success-message" role="status">
                  <Check size={20} aria-hidden="true" />
                  <strong>Chào mừng bạn đến với CORTIS Club!</strong>
                  <span>Mã ưu đãi độc quyền đã được kích hoạt cho tài khoản của bạn.</span>
                </div>
              ) : (
                <form onSubmit={handleVipSubmit} className="vip-form" aria-label="Đăng ký nhận tin">
                  <div className="vip-input-wrap">
                    <input
                      type="email"
                      required
                      placeholder="Nhập địa chỉ email của bạn…"
                      value={vipEmail}
                      onChange={e => setVipEmail(e.target.value)}
                      className="vip-input"
                    />
                    <button type="submit" className="primary-button vip-submit-btn">
                      <span>Đăng ký thành viên</span>
                      <ArrowRight size={16} aria-hidden="true" />
                    </button>
                  </div>
                  <small className="vip-disclaimer">
                    Chúng tôi tôn trọng quyền riêng tư của bạn. Không gửi thư rác.
                  </small>
                </form>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* 9. Provenance & Photo Credits Notice */}
      <section className="landing-credits-section" aria-label="Ghi công hình ảnh">
        <div className="section-container">
          <div className="credits-compact-panel">
            <div className="credits-header">
              <small>GHI NHẬN NGUỒN ẢNH VÀ GIẤY PHÉP (IMAGE CREDITS & ATTRIBUTION)</small>
            </div>
            <p>
              Tất cả ảnh của nhóm nhạc <strong>CORTIS</strong> trang trí trên trang này được lưu trữ và tải từ Wikimedia Commons,
              thuộc quyền tác giả của <em>TikTok Awards Korea</em>, <em>SBS Radio (Cultwo Show)</em>, <em>Newsen</em>, và các cộng tác viên Wikimedia Commons
              dưới giấy phép Creative Commons (CC BY 3.0 / CC BY-SA 4.0).
              Các sản phẩm giày, túi và trang phục trưng bày sử dụng ảnh thật có xuất xứ được ghi chi tiết tại{' '}
              <Link to="/credits" className="text-link">Trang Nguồn Ảnh</Link>.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
