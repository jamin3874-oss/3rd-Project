# SpendWise Android 1.0.0

앱 아이콘을 누르면 HTTPS로 배포된 SpendWise가 열린다. 로그인과 거래 내역은 웹과 동일하며, 통신과 쿠키 처리는 휴대폰의 브라우저가 담당한다. 별도 앱 권한이 필요하지 않다. 기본 브라우저가 맞춤 탭을 지원하면 맞춤 탭에서, 그 밖에는 브라우저 창에서 가계부를 연다.

## 설치

[서명된 APK 내려받기](https://raw.githubusercontent.com/jamin3874-oss/3rd-Project/main/2%EB%B2%88%20%EA%B3%BC%EC%A0%9C/spendwise_agent/android/SpendWise.apk) · Android 7.0 이상 · 패키지 이름 `io.github.jamin3874.spendwise`

다운로드한 파일을 열고 설치한 뒤 앱 목록에서 SpendWise를 누른다. 아이폰은 웹 주소를 Safari 홈 화면에 추가해 사용할 수 있다.

## 새 버전 빌드

배포 APK의 SHA-256은 `a74c8605a68d2e710622f7af8b05110079e42aefdea6195012ce87c7d720e46d`다. Android SDK에서 v2·v3 서명, 패키지 이름, API 대상 버전과 정렬을 검사했다. [검증 화면](../evidence/submission-verification.jpg)

Linux에서 JDK 17 이상, Android SDK Platform 35, Build Tools 35.0.0 및 zip을 준비한다. `ANDROID_HOME`에 SDK 경로를 설정한다. `SPENDWISE_KEYSTORE`에 기존 PKCS12 서명키 경로를, `SPENDWISE_STORE_PASS`에 해당 비밀번호를 실행 환경에서 제공한다. 키 별칭은 `spendwise`다.

이 폴더에서 `bash build.sh`를 실행하면 패키지 서명과 정렬을 확인한 뒤 `SpendWise.apk`가 생성된다. 휴대폰에 업데이트를 배포할 때는 같은 서명키를 사용하고 매니페스트의 versionCode를 올린다. 웹 화면과 서버만 바뀔 때는 휴대폰에서 다시 설치할 필요가 없다.
