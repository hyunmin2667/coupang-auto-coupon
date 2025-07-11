# coupang_lib/item_loader.py
import pandas as pd

def load_vendor_items_from_csv(file_path="vendor_items.csv") -> list:
    """
    제목 열이 없는 CSV 파일에서 vendor items를 로드합니다.
    CSV 파일은 단일 컬럼으로 구성되며, 그 값이 상품 ID로 직접 사용됩니다.
    """
    try:
        df = pd.read_csv(file_path, header=None, names=['item_id'])
        if df.empty:
            print(f"오류: '{file_path}' 파일에 데이터가 없습니다.")
            return []

        # 이제 딕셔너리 리스트가 아닌, ID 값의 리스트를 반환합니다.
        # ID가 숫자로 필요하다면 int(), 문자열로 필요하다면 str()로 변환합니다.
        # API는 보통 ID를 문자열로 받으므로, str()이 안전합니다.
        vendor_items_list = df['item_id'].astype(str).tolist() 

        print(f"CSV 파일 '{file_path}'에서 VENDOR_ITEMS 로드 완료 (단순 ID 리스트).")
        return vendor_items_list
    except FileNotFoundError:
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다. 파일 경로를 확인해주세요.")
        return []
    except Exception as e:
        print(f"오류: CSV 파일 로드 중 문제가 발생했습니다: {e}")
        return []