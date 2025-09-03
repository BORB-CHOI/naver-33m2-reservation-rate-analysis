// app/types.d.ts (기존 타입에 추가)
declare global {
  const kakao: any;
}

export interface NaverProperty {
  매물제목: string;
  층수정보: string;
  위도: number;
  경도: number;
  보증금: number | null;
  월세: number | null;
  매물ID: string;
  동일주소매물수: number;
  전용면적: number;
  주소?: string;
  건물명?: string;
  동일주소_최대보증금: number;
  동일주소_최소보증금: number;
  동일주소_최대월세: number;
  동일주소_최소월세: number;
}

export interface SamProperty {
  rid: number;
  room_name: string;
  addr_street: string;
  using_fee: number | null;
  occupancy_rate_percent: number | null;
  room_cnt: number;
  bathroom_cnt: number;
  cookroom_cnt: number;
  sittingroom_cnt: number;
  longterm_discount_per: number;
  early_discount_per: number;
  lat: number;
  lng: number;
}

// 새로 추가된 서울 오피스텔 타입
export interface SeoulProperty {
  rid: number;
  room_name: string;
  state: string;
  province: string;
  town: string;
  pic_main: string;
  addr_lot: string;
  addr_street: string;
  using_fee: number | null;
  pyeong_size: number;
  room_cnt: number;
  bathroom_cnt: number;
  cookroom_cnt: number;
  sittingroom_cnt: number;
  reco_type_1: string;
  reco_type_2: string;
  longterm_discount_per: number;
  early_discount_per: number;
  is_new: boolean;
  is_super_host: boolean;
  lat: number;
  lng: number;
  crawl_datetime: string;
  crawl_timestamp: number;
  search_keyword: string;
}

export interface Property {
  id: string;
  source: "naver" | "sam" | "seoul";
  raw: NaverProperty | SamProperty | SeoulProperty;
  title: string;
  lat: number;
  lng: number;
  addr: string;
  deposit?: number;
  rent?: number;
  occupancy?: number;
}
