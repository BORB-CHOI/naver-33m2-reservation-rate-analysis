// app/profit/components/ProfitMap.tsx
"use client";

import { useState, useEffect, useRef } from "react";
import {
  Map as KakaoMap,
  MapMarker,
  MapInfoWindow,
} from "react-kakao-maps-sdk";
import Papa from "papaparse";
import type { Property, NaverProperty, SeoulProperty } from "../../types";
import KakaoScript from "../../components/KakaoScript";

/*────────────────── 헬퍼 ──────────────────*/
// 더 관대한 좌표 그룹핑 (소수 3자리 → 약 111m 오차)
const coordKey = (lat: number, lng: number) =>
  `${Math.round(lat * 1e3)}/${Math.round(lng * 1e3)}`; // 소수 3자리(≈111 m)

// 수익 금액에 따른 핀 색상 결정 (원 단위)
const profitColor = (profitAmount: number) => {
  if (profitAmount >= 700000) return "green"; // 70만 이상
  if (profitAmount >= 500000) return "blue"; // 50만~70만
  if (profitAmount >= 300000) return "yellow"; // 30만~50만
  if (profitAmount >= 200000) return "orange"; // 20만~30만
  return "red"; // 20만 미만
};

// 서울 오피스텔 월 수익 계산 (기본 공식)
const monthlyRevenue = (p: SeoulProperty) => (p.using_fee ?? 0) * 4;

// 수익률 계산: (서울오피스텔 금액 * 4 - 네이버 월세) / 네이버 월세 * 100
const calculateProfitRate = (seoulRevenue: number, naverRent: number) => {
  if (naverRent === 0) return 0;
  return ((seoulRevenue - naverRent * 10_000) / (naverRent * 10_000)) * 100;
};

// 서울오피스텔: 평 → 제곱미터 변환
const toM2 = (pyeong: number | null | undefined) =>
  pyeong == null ? null : Math.round(pyeong * 3.3058);

// 네이버: 제곱미터 → 평 변환
const toPyeong = (m2: number | null | undefined) =>
  m2 == null ? null : Math.round((m2 / 3.3058) * 10) / 10; // 소수 1자리

const fmt = (n: number | null | undefined, unit = "") =>
  n == null ? "—" : `${n.toLocaleString()}${unit}`;

/*────────────────── 컴포넌트 ──────────────────*/
export default function ProfitMap() {
  const [groups, setGroups] = useState<Map<string, Property[]>>(new Map());
  const [addressGroups, setAddressGroups] = useState<Map<string, Property[]>>(
    new Map()
  );
  const [selected, setSelected] = useState<Property[] | null>(null);
  const [useAddressGrouping, setUseAddressGrouping] = useState(false);
  const geocoderRef = useRef<any>(null);

  // 역지오코딩으로 주소 가져오기
  const getAddressFromCoords = (lat: number, lng: number): Promise<string> => {
    return new Promise((resolve) => {
      if (!geocoderRef.current || !window.kakao) {
        resolve("unknown");
        return;
      }

      const coord = new window.kakao.maps.LatLng(lat, lng);
      geocoderRef.current.coord2Address(
        coord.getLng(),
        coord.getLat(),
        (result: any, status: any) => {
          if (
            status === window.kakao.maps.services.Status.OK &&
            result.length > 0
          ) {
            // 시군구 단위로 그룹핑 (예: "서울특별시 강남구")
            const addr = result[0].address || result[0].road_address;
            if (addr) {
              const addressKey = `${addr.region_1depth_name} ${addr.region_2depth_name}`;
              resolve(addressKey);
              return;
            }
          }
          resolve("unknown");
        }
      );
    });
  };

  // 주소 기반 그룹핑
  const groupByAddress = async (properties: Property[]) => {
    const addressMap = new Map<string, Property[]>();

    for (const prop of properties) {
      const addressKey = await getAddressFromCoords(prop.lat, prop.lng);
      if (!addressMap.has(addressKey)) {
        addressMap.set(addressKey, []);
      }
      addressMap.get(addressKey)!.push(prop);
    }

    setAddressGroups(addressMap);
  };

  /* CSV 로드 */
  useEffect(() => {
    const loadData = async () => {
      const [naverCsv, seoulCsv] = await Promise.all([
        fetch("/naver/naver_20250808_035438_final.csv").then((r) => r.text()),
        fetch("/room/room_250803.csv").then((r) => r.text()),
      ]);

      /* 네이버 */
      const nRows = Papa.parse<NaverProperty>(naverCsv, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
      }).data.filter(
        (r) => typeof r.위도 === "number" && typeof r.경도 === "number"
      );

      const nProps: Property[] = nRows.map((r) => ({
        id: r.매물ID,
        source: "naver",
        raw: r,
        title: r.매물제목 ?? "—",
        lat: r.위도,
        lng: r.경도,
        addr: r.주소 ?? "—",
        deposit: r.보증금 ?? undefined,
        rent: r.월세 ?? undefined,
      }));

      /* 서울 오피스텔 */
      const sRows = Papa.parse<SeoulProperty>(seoulCsv, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
      }).data.filter(
        (r) => typeof r.lat === "number" && typeof r.lng === "number"
      );

      const sProps: Property[] = sRows.map((r) => ({
        id: String(r.rid),
        source: "seoul",
        raw: r,
        title: r.room_name ?? "—",
        lat: r.lat,
        lng: r.lng,
        addr: r.addr_street ?? "—",
        deposit: r.using_fee ?? undefined,
        occupancy: undefined,
      }));

      /* 좌표별 그룹 */
      const map = new Map<string, Property[]>();
      [...nProps, ...sProps].forEach((p) => {
        const k = coordKey(p.lat, p.lng);
        if (!map.has(k)) map.set(k, []);
        map.get(k)!.push(p);
      });
      setGroups(map);

      // 카카오 지도 로드 후 지오코더 초기화
      if (window.kakao && window.kakao.maps) {
        window.kakao.maps.load(() => {
          geocoderRef.current = new window.kakao.maps.services.Geocoder();
        });
      }
    };

    loadData();
  }, []);

  /* 마커 아이콘 */
  const iconOf = (g: Property[]) => {
    const seoulList = g.filter((p) => p.source === "seoul");
    const naverList = g.filter((p) => p.source === "naver");

    // 1) 네이버 + 서울오피스텔 겹침 → 수익 금액 기반 색상
    if (seoulList.length && naverList.length) {
      const naverAvgRent =
        naverList.reduce((s, p) => s + (p.rent ?? 0), 0) / naverList.length;

      const avgProfitAmount =
        seoulList.reduce((sum, p) => {
          const revenue = monthlyRevenue(p.raw as SeoulProperty);
          const diff = revenue - naverAvgRent * 10_000;
          return sum + diff;
        }, 0) / seoulList.length;

      return `/pin-${profitColor(avgProfitAmount)}.svg`;
    }

    // 2) 서울오피스텔 단독 → 비교 대상 없으므로 기본색
    if (seoulList.length) {
      return "/pin-purple.svg";
    }

    // 3) 네이버 단독
    return "/home-default.svg";
  };

  /* InfoWindow 토글 */
  const openInfo = (g: Property[]) => {
    setSelected(null);
    requestAnimationFrame(() => setSelected(g));
  };

  /* 네이버 평균 월세 계산 (해당 그룹) */
  const getNaverAvgRent = (g: Property[]) => {
    const navers = g.filter((p) => p.source === "naver");
    if (!navers.length) return null;
    return navers.reduce((s, p) => s + (p.rent ?? 0), 0) / navers.length;
  };

  // 현재 사용할 그룹 결정
  const currentGroups = useAddressGrouping ? addressGroups : groups;

  // 마커 렌더링 순서 조정을 위한 그룹 분리
  const naverOnlyGroups = Array.from(currentGroups.entries()).filter(
    ([, g]) => {
      const seoulList = g.filter((p) => p.source === "seoul");
      const naverList = g.filter((p) => p.source === "naver");
      return naverList.length > 0 && seoulList.length === 0;
    }
  );

  const seoulGroups = Array.from(currentGroups.entries()).filter(([, g]) => {
    const seoulList = g.filter((p) => p.source === "seoul");
    return seoulList.length > 0;
  });

  // 주소 기반 그룹핑 토글 핸들러
  const handleAddressGrouping = async () => {
    if (!useAddressGrouping && geocoderRef.current) {
      const allProperties = Array.from(groups.values()).flat();
      await groupByAddress(allProperties);
    }
    setUseAddressGrouping(!useAddressGrouping);
  };

  /*────────────────── 렌더 ──────────────────*/
  return (
    <>
      <KakaoScript />

      {/* 그룹핑 방식 선택 버튼 */}
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          zIndex: 1000,
          backgroundColor: "white",
          padding: "10px",
          borderRadius: "5px",
          boxShadow: "0 2px 5px rgba(0,0,0,0.2)",
        }}
      >
        <button
          onClick={handleAddressGrouping}
          style={{
            padding: "8px 12px",
            backgroundColor: useAddressGrouping ? "#007bff" : "#f8f9fa",
            color: useAddressGrouping ? "white" : "black",
            border: "1px solid #ccc",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          {useAddressGrouping ? "주소 그룹핑 ON" : "주소 그룹핑 OFF"}
        </button>
        <div style={{ fontSize: "12px", marginTop: "5px", color: "#666" }}>
          {useAddressGrouping
            ? "시군구 단위로 그룹핑 중"
            : "좌표 기반 그룹핑 중 (111m 반경)"}
        </div>
      </div>

      <KakaoMap
        center={{ lat: 37.5665, lng: 126.978 }}
        level={6}
        style={{ width: "100%", height: "100vh" }}
      >
        {/* 네이버 단독 마커 먼저 렌더링 (뒤에 위치) */}
        {naverOnlyGroups.map(([k, g]) => {
          // 그룹의 대표 좌표 계산 (평균)
          const avgLat = g.reduce((sum, p) => sum + p.lat, 0) / g.length;
          const avgLng = g.reduce((sum, p) => sum + p.lng, 0) / g.length;

          return (
            <MapMarker
              key={`naver-${k}`}
              position={{ lat: avgLat, lng: avgLng }}
              image={{
                src: iconOf(g),
                size: { width: 32, height: 32 },
                options: { offset: { x: 16, y: 32 } },
              }}
              onClick={() => openInfo(g)}
            />
          );
        })}

        {/* 서울오피스텔 포함 마커 나중에 렌더링 (앞에 위치) */}
        {seoulGroups.map(([k, g]) => {
          const avgLat = g.reduce((sum, p) => sum + p.lat, 0) / g.length;
          const avgLng = g.reduce((sum, p) => sum + p.lng, 0) / g.length;

          return (
            <MapMarker
              key={`seoul-${k}`}
              position={{ lat: avgLat, lng: avgLng }}
              image={{
                src: iconOf(g),
                size: { width: 32, height: 32 },
                options: { offset: { x: 16, y: 32 } },
              }}
              onClick={() => openInfo(g)}
            />
          );
        })}

        {/* InfoWindow */}
        {selected && (
          <MapInfoWindow
            key={`info-${selected[0].id}-${Date.now()}`}
            position={{
              lat:
                selected.reduce((sum, p) => sum + p.lat, 0) / selected.length,
              lng:
                selected.reduce((sum, p) => sum + p.lng, 0) / selected.length,
            }}
            removable
            onCloseClick={() => setSelected(null)}
          >
            {/* 스크롤 가능 영역 */}
            <div
              style={{
                padding: 16,
                minWidth: 300,
                maxWidth: 520,
                maxHeight: "60vh",
                overflowY: "auto",
                fontSize: 14,
                lineHeight: 1.4,
              }}
            >
              <div
                style={{ marginBottom: 10, fontWeight: "bold", color: "#333" }}
              >
                매물 {selected.length}건 (
                {useAddressGrouping ? "주소 기반" : "좌표 기반"} 그룹핑)
              </div>

              {selected.map((p, idx) =>
                p.source === "naver" ? (
                  /* ─── 네이버 ─── */
                  <div
                    key={`naver-${p.id}-${idx}`}
                    style={{ marginBottom: 12 }}
                  >
                    <strong style={{ color: "#15803d" }}>네이버</strong>
                    <br />
                    매물명: {(p.raw as NaverProperty).매물제목}
                    <br />
                    주소: {(p.raw as NaverProperty).주소}
                    <br />
                    전용면적:{" "}
                    {fmt(
                      toPyeong((p.raw as NaverProperty).전용면적),
                      "평"
                    )} / {fmt((p.raw as NaverProperty).전용면적, "㎡")}
                    <br />
                    보증금: {fmt((p.raw as NaverProperty).보증금, "만 원")}
                    <br />
                    월세: {fmt((p.raw as NaverProperty).월세, "만 원")}
                    <br />
                    동일주소 매물수: {(p.raw as NaverProperty).동일주소매물수}
                    <br />
                    최대보증금:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최대보증금, "만 원")}
                    <br />
                    최소보증금:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최소보증금, "만 원")}
                    <br />
                    최대월세:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최대월세, "만 원")}
                    <br />
                    최소월세:{" "}
                    {fmt((p.raw as NaverProperty).동일주소_최소월세, "만 원")}
                  </div>
                ) : (
                  /* ─── 서울 오피스텔 ─── */
                  <div
                    key={`seoul-${p.id}-${idx}`}
                    style={{ marginBottom: 12 }}
                  >
                    <strong style={{ color: "#1d4ed8" }}>서울 오피스텔</strong>
                    <br />
                    매물명: {(p.raw as SeoulProperty).room_name}
                    <br />
                    주소: {(p.raw as SeoulProperty).addr_street}
                    <br />
                    평형: {fmt(
                      (p.raw as SeoulProperty).pyeong_size,
                      "평"
                    )} / {fmt(toM2((p.raw as SeoulProperty).pyeong_size), "㎡")}
                    <br />
                    1주당 금액: {fmt((p.raw as SeoulProperty).using_fee, "원")}
                    <br />
                    방/욕실/주방/거실: {(p.raw as SeoulProperty).room_cnt}/
                    {(p.raw as SeoulProperty).bathroom_cnt}/
                    {(p.raw as SeoulProperty).cookroom_cnt}/
                    {(p.raw as SeoulProperty).sittingroom_cnt}
                    <br />
                    장기 할인율:{" "}
                    {(p.raw as SeoulProperty).longterm_discount_per}%
                    <br />
                    얼리버드 할인율:{" "}
                    {(p.raw as SeoulProperty).early_discount_per}
                    %<br />
                    <em style={{ color: "#16a34a", fontWeight: 600 }}>
                      월 기본 수익:{" "}
                      {monthlyRevenue(p.raw as SeoulProperty).toLocaleString()}
                      원
                    </em>
                    {(() => {
                      const naverAvg = getNaverAvgRent(selected);
                      if (naverAvg == null) {
                        return (
                          <>
                            <br />
                            <span style={{ color: "#666" }}>
                              (네이버 매물 없음 - 수익률 계산 불가)
                            </span>
                          </>
                        );
                      }

                      const revenue = monthlyRevenue(p.raw as SeoulProperty);
                      const profitRate = calculateProfitRate(revenue, naverAvg);
                      const diff = revenue - naverAvg * 10_000;

                      return (
                        <>
                          <br />
                          <span style={{ fontSize: 12, color: "#666" }}>
                            네이버 평균 월세: {naverAvg.toLocaleString()}만원
                          </span>
                          <br />
                          <span
                            style={{
                              color: profitRate >= 0 ? "#16a34a" : "#dc2626",
                              fontWeight: 600,
                            }}
                          >
                            수익률: {profitRate >= 0 ? "+" : ""}
                            {profitRate.toFixed(1)}%
                          </span>
                          <br />
                          <span
                            style={{
                              color: diff >= 0 ? "#16a34a" : "#dc2626",
                            }}
                          >
                            금액 차액: {diff >= 0 ? "+" : ""}
                            {diff.toLocaleString()}원
                          </span>
                        </>
                      );
                    })()}
                  </div>
                )
              )}
            </div>
          </MapInfoWindow>
        )}
      </KakaoMap>
    </>
  );
}
