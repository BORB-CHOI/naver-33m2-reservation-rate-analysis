// app/components/KakaoScript.tsx
"use client";
import Script from "next/script";

export default function KakaoScript() {
  return (
    <Script
      src={`//dapi.kakao.com/v2/maps/sdk.js?appkey=${process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY}&libraries=clusterer,services&autoload=false`}
      strategy="beforeInteractive"
    />
  );
}
