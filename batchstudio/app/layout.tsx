import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'BatchStudio — make one, make many',description:'An open-source, local-first studio for data-driven posters, badges and coupons.',icons:{icon:'/favicon.svg'}};
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>;}
