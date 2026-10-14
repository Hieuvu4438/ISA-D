import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, getAccount, loginAccount, registerAccount, logoutAccount, updateProfile, changePassword, getAdminOverview, type AccountUser } from '../lib/api'
import { ErrorPanel } from '../ui'

export function AccountPage() {
  const [user, setUser] = useState<AccountUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [overview, setOverview] = useState<{ accounts: Record<string, number>; products: number; orders: number } | null>(null)
  const active = useRef(true)
  const locked = useRef(false)
  useEffect(() => {
    active.current = true
    const controller = new AbortController()
    setLoading(true)
    getAccount(controller.signal).then(result => {
      if (!controller.signal.aborted) setUser(result.user)
    }).catch(reason => {
      if (!controller.signal.aborted && !(reason instanceof ApiError && reason.status === 401)) setError(reason instanceof Error ? reason.message : 'Chưa tải được tài khoản.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { active.current = false; controller.abort() }
  }, [attempt])
  useEffect(() => {
    const controller = new AbortController()
    setOverview(null)
    if (user?.role === 'admin') getAdminOverview(controller.signal).then(result => {
      if (!controller.signal.aborted) setOverview(result)
    }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Chưa tải được tổng quan.') })
    return () => controller.abort()
  }, [user])
  async function perform(action: () => Promise<void>) {
    if (locked.current) return
    locked.current = true
    setBusy(true); setError(null); setNotice('')
    try { await action() }
    catch (reason) {
      if (active.current) {
        setError(reason instanceof Error ? reason.message : 'Chưa hoàn tất. Vui lòng thử lại.')
        if (reason instanceof ApiError && reason.code === 'AUTH_REQUIRED') setUser(null)
      }
    } finally { locked.current = false; if (active.current) setBusy(false) }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = new FormData(form)
    const email = String(values.get('email')), password = String(values.get('password'))
    void perform(async () => {
      const result = mode === 'register' ? await registerAccount(email, password, String(values.get('display_name'))) : await loginAccount(email, password)
      if (active.current) { setUser(result.user); form.reset(); setNotice('Đã đăng nhập.') }
    })
  }
  return <div className="page-shell account-page">
    <header className="page-heading"><h1>Tài khoản của bạn.</h1><p>Quản lý thông tin và truy cập đơn hàng của bạn.</p></header>
    {loading ? <p role="status">Đang tải tài khoản…</p> : <>
      {error && <ErrorPanel message={error} onRetry={user ? undefined : () => { setError(null); setAttempt(value => value + 1) }} />}
      {notice && <p className="account-notice" role="status">{notice}</p>}
      {!user ? <section className="account-panel" aria-label="Đăng nhập hoặc tạo tài khoản">
        <div className="account-mode"><button className={mode === 'login' ? 'primary-button' : 'secondary-button'} disabled={busy} onClick={() => { setMode('login'); setError(null) }}>Đăng nhập</button><button className={mode === 'register' ? 'primary-button' : 'secondary-button'} disabled={busy} onClick={() => { setMode('register'); setError(null) }}>Tạo tài khoản</button></div>
        <h2>{mode === 'login' ? 'Chào mừng trở lại' : 'Bắt đầu cùng Cortis'}</h2>
        <form key={mode} className="account-form" onSubmit={submit}>
          <fieldset disabled={busy}>
            {mode === 'register' && <label>Tên hiển thị<input name="display_name" autoComplete="name" required maxLength={80} /></label>}
            <label>Email<input name="email" type="email" autoComplete="email" required maxLength={254} /></label>
            <label>Mật khẩu<input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'register' ? 15 : 1} maxLength={128} aria-describedby={mode === 'register' ? 'password-hint' : undefined} /></label>
            {mode === 'register' && <p id="password-hint">Dùng cụm mật khẩu từ 15 đến 128 ký tự.</p>}
            <button className="primary-button" type="submit">{busy ? 'Đang xử lý…' : mode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản'}</button>
          </fieldset>
        </form>
      </section> : <div className="account-layout">
        <section className="account-panel"><h2>{user.display_name}</h2><p className="account-email">{user.email}</p><p>{user.role === 'admin' ? 'Quản trị viên' : 'Khách hàng'}</p>
          <div className="account-mode"><Link className="primary-button" to="/orders">Xem đơn hàng</Link><button className="secondary-button" disabled={busy} onClick={() => { void perform(async () => { await logoutAccount(); if (active.current) { setUser(null); setNotice('Đã đăng xuất.') } }) }}>Đăng xuất</button></div>
          <form className="account-form" onSubmit={event => {
            event.preventDefault(); const data = new FormData(event.currentTarget)
            void perform(async () => { const result = await updateProfile(String(data.get('display_name'))); if (active.current) { setUser(result.user); setNotice('Đã lưu tên hiển thị.') } })
          }}><h3>Thông tin cá nhân</h3><fieldset disabled={busy}><label>Tên hiển thị<input key={user.display_name} name="display_name" defaultValue={user.display_name} required maxLength={80} autoComplete="name" /></label><button className="secondary-button">Lưu thông tin</button></fieldset></form>
        </section>
        <section className="account-panel"><h2>Đổi mật khẩu</h2><p>Các phiên đăng nhập khác sẽ kết thúc sau khi đổi mật khẩu.</p>
          <form className="account-form" onSubmit={event => {
            event.preventDefault(); const form = event.currentTarget; const data = new FormData(form)
            if (data.get('password') !== data.get('confirm')) { setError('Mật khẩu xác nhận chưa khớp.'); return }
            void perform(async () => { await changePassword(String(data.get('current_password')), String(data.get('password'))); if (active.current) { form.reset(); setNotice('Đã đổi mật khẩu và kết thúc các phiên khác.') } })
          }}><fieldset disabled={busy}>
            <label>Mật khẩu hiện tại<input name="current_password" type="password" autoComplete="current-password" required maxLength={128} /></label>
            <label>Mật khẩu mới<input name="password" type="password" autoComplete="new-password" required minLength={15} maxLength={128} /></label>
            <label>Xác nhận mật khẩu mới<input name="confirm" type="password" autoComplete="new-password" required minLength={15} maxLength={128} /></label>
            <button className="primary-button">Đổi mật khẩu</button>
          </fieldset></form>
        </section>
        {user.role === 'admin' && <section className="account-panel"><h2>Tổng quan quản trị</h2><Link className="primary-button" to="/admin">Mở trang quản trị</Link>{overview ? <dl className="account-counts"><dt>Sản phẩm</dt><dd>{overview.products}</dd><dt>Đơn hàng minh họa</dt><dd>{overview.orders}</dd><dt>Khách hàng</dt><dd>{overview.accounts.user ?? 0}</dd><dt>Quản trị viên</dt><dd>{overview.accounts.admin ?? 0}</dd></dl> : <p role="status">Đang tải tổng quan…</p>}</section>}
      </div>}
    </>}
  </div>
}
