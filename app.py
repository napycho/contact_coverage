import streamlit as st
import pandas as pd
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 페이지 제목
st.title("커버리지 검색 시스템")

# 설정값
CREDENTIALS_FILE = 'adept-button-450108-a8-402400d776a2.json'
SPREADSHEET_ID = '1AzOZiJmEJApw9WUQj33IDaRq1pGX2mMqZ-4V9hK1FTg'
KAKAO_API_KEY = '6134aed5a8e4bbf5b758347bd19b4989'

def normalize_region(region):
    """지역명 정규화"""
    region_mapping = {
        '서울': '서울특별시',
        '부산': '부산광역시',
        '대구': '대구광역시',
        '인천': '인천광역시',
        '광주': '광주광역시',
        '대전': '대전광역시',
        '울산': '울산광역시',
        '세종': '세종특별자치시',
        '경기': '경기도',
        '강원': '강원특별자치도',
        '충북': '충청북도',
        '충남': '충청남도',
        '전북': '전라북도',
        '전남': '전라남도',
        '경북': '경상북도',
        '경남': '경상남도',
        '제주': '제주특별자치도'
    }
    
    base_region = region.split()[0]
    return region_mapping.get(base_region, region)

def get_coverage_info(address):
    """커버리지 정보 검색"""
    try:
        # 카카오 API로 주소 검색
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"query": address}
        
        response = requests.get(url, headers=headers, params=params)
        result = response.json()
        
        if not result.get('documents'):
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
        if not result.get('documents'):
            return None
            
        place = result['documents'][0]
        address_info = place.get('address', place.get('road_address'))
        if not address_info:
            return None
            
        sido = normalize_region(address_info.get('region_1depth_name', ''))
        sigungu = address_info.get('region_2depth_name', '')
        dong = address_info.get('region_3depth_name', '')
        
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=credentials)
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='커버리지 가져오기!A:Q'
        ).execute()
        
        df = pd.DataFrame(result['values'][1:], columns=result['values'][0])
        
        mask = df['지역'] == sido
        
        if sigungu:
            sigungu_simple = sigungu.split()[-1]
            mask = mask & df['시군구명'].str.contains(sigungu_simple, na=False)
        
        filtered_df = df[mask]
        
        if len(filtered_df) > 0:
            result = filtered_df.iloc[0]
            return {
                '검색주소': address,
                '시도': sido,
                '시군구': sigungu,
                '동': dong,
                '매칭된주소': result['지역 합치기'],
                '주간보호(P1)': result['주간보호(P1)'],
                '주간보호(P2)': result['주간보호(P2)'],
                '방문요양(1~4등급)': result['방문요양(1~4등급)\n/방문목욕'],
                '방문요양(5등급)': result['방문요양(5등급)'],
                '차량목욕': result['차량목욕'],
                '방문간호': result['방문간호'],
                '복지용구': result['복지용구'],
                '센터담당자': result['센터 담당자'],
                '센터연락처': result['센터 담당자\n연락처'],
                '본부담당자': result['본부 담당자'],
                '계약전건강검진': result['계약전 건강검진 \n필수 여부']
            }
            
        return None
        
    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
        return None

# 주소 입력 UI
address = st.text_input("주소를 입력하세요", 
                     placeholder="예: 강남구 역삼동, 분당구 정자동",
                     help="동이나 구 단위로 입력해주세요")

# 검색 버튼
if st.button("검색", type="primary"):
    if address:
        with st.spinner("검색 중..."):
            result = get_coverage_info(address)
            
            if result:
                st.success("검색 완료!")
                
                # 지역 정보
                st.subheader("📍 지역 정보")
                st.info(f"검색주소: {result['검색주소']}\n매칭된 주소: {result['매칭된주소']}")
                
                # 서비스 정보를 탭으로 표시
                tab1, tab2, tab3, tab4, tab5 = st.tabs(["주간보호", "방문요양", "차량목욕", "방문간호", "복지용구"])
                
                with tab1:
                    st.write("### 🏥 주간보호")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**P1:**", result['주간보호(P1)'] or "서비스 없음")
                    with col2:
                        st.write("**P2:**", result['주간보호(P2)'] or "서비스 없음")
                
                with tab2:
                    st.write("### 🏠 방문요양")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**1~4등급:**", result['방문요양(1~4등급)'])
                    with col2:
                        st.write("**5등급:**", result['방문요양(5등급)'])
                
                with tab3:
                    st.write("### 🚗 차량목욕")
                    st.write(result['차량목욕'] or "서비스 없음")
                
                with tab4:
                    st.write("### 👨‍⚕️ 방문간호")
                    st.write(result['방문간호'] or "서비스 없음")
                
                with tab5:
                    st.write("### 🛠️ 복지용구")
                    st.write(result['복지용구'] or "서비스 없음")
                
                # 담당자 정보
                st.subheader("👥 담당자 정보")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**센터 담당자:**", result['센터담당자'])
                    st.write("**연락처:**", result['센터연락처'])
                with col2:
                    st.write("**본부 담당자:**", result['본부담당자'])
                
                # 추가 정보
                st.subheader("ℹ️ 추가 정보")
                st.write("**계약전 건강검진 필수 여부:**", result['계약전건강검진'])
                
            else:
                st.warning("해당 지역의 커버리지 정보를 찾을 수 없습니다.")
    else:
        st.warning("주소를 입력해주세요.")
