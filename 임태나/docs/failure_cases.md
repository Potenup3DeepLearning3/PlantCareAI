# 실패 케이스 로그

**생성 일시**: 2026-04-01 23:52
**총 오분류 건수**: 97

## 주요 오분류 패턴

| 실제 | 예측 | 건수 |
|------|------|------|
| Healthy | Blight_Spot | 24 |
| Rust | Blight_Spot | 15 |
| Scab_Rot | Blight_Spot | 10 |
| Blight_Spot | Rust | 6 |
| Leaf_Mold | Blight_Spot | 6 |
| Mosaic_Virus | Blight_Spot | 5 |
| Leaf_Curl | Blight_Spot | 5 |
| Blight_Spot | Healthy | 4 |
| Mosaic_Virus | Healthy | 4 |
| Scab_Rot | Healthy | 3 |
| Powdery_Mildew | Healthy | 3 |
| Scab_Rot | Rust | 2 |
| Healthy | Scab_Rot | 2 |
| Healthy | Greening | 1 |
| Blight_Spot | Scab_Rot | 1 |
| Healthy | Mosaic_Virus | 1 |
| Healthy | Leaf_Curl | 1 |
| Powdery_Mildew | Blight_Spot | 1 |
| Blight_Spot | Leaf_Mold | 1 |
| Mosaic_Virus | Leaf_Curl | 1 |

## 상세 실패 케이스 (상위 50건)

| 이미지 | 원본 클래스 | 실제 | 예측 | 신뢰도 |
|--------|-----------|------|------|--------|
| 20180511_090912-14gtw8a-e1526047952754.jpg | Apple leaf | Healthy | Blight_Spot | 0.9446 |
| apple-leaf-isolated-white-background-56631026.jpg | Apple leaf | Healthy | Greening | 0.5786 |
| 02.-Rust-2017-207u24s.jpg | Apple rust leaf | Rust | Blight_Spot | 0.5571 |
| 185161-004-EAF28842.jpg | Apple rust leaf | Rust | Blight_Spot | 0.9076 |
| 2011-011.jpg | Apple rust leaf | Rust | Blight_Spot | 0.9968 |
| 20130519cedarapplerust.jpg | Apple rust leaf | Rust | Blight_Spot | 0.9864 |
| 20130802_111632.jpg | Apple rust leaf | Rust | Blight_Spot | 0.8794 |
| 9343310-small.jpg | Apple rust leaf | Rust | Blight_Spot | 0.7321 |
| 99e886623c2080c22f6519b0e708c531.jpg | Apple rust leaf | Rust | Blight_Spot | 0.4691 |
| 052609%20Hartman%20Crabapple%20scab%20single%20leaf.JPG.jpg | Apple Scab Leaf | Scab_Rot | Blight_Spot | 0.9992 |
| 1b321015-6e33-4f18-aade-888f4383fe92.jpeg.jpg | Apple Scab Leaf | Scab_Rot | Blight_Spot | 1.0000 |
| 28-500x375.jpg | Apple Scab Leaf | Scab_Rot | Blight_Spot | 0.9253 |
| apple%20scab%20leaf.jpg | Apple Scab Leaf | Scab_Rot | Rust | 0.6677 |
| apple%20scabnew.jpg | Apple Scab Leaf | Scab_Rot | Healthy | 0.4647 |
| apple-scab-5366820.jpg | Apple Scab Leaf | Scab_Rot | Blight_Spot | 1.0000 |
| apples_apple-scab_01_zoom.jpg | Apple Scab Leaf | Scab_Rot | Blight_Spot | 0.7909 |
| apples_apple-scab_02_thm.jpg | Apple Scab Leaf | Scab_Rot | Blight_Spot | 0.8963 |
| apples_apple-scab_10_zoom.jpg | Apple Scab Leaf | Scab_Rot | Healthy | 0.2859 |
| IMG_1629.JPG_1507122477.jpg | Bell_pepper leaf | Healthy | Blight_Spot | 0.9475 |
| blueberry-leaves-normal-above-and-iron-deficient-below-bgahf8.jpg | Blueberry leaf | Healthy | Blight_Spot | 0.6269 |
| blueberrysilverleaf16-1372b.jpg | Blueberry leaf | Healthy | Blight_Spot | 0.9073 |
| P1200701+Vaccinium+ovalifolium+Oval-leaf+Blueberry+leaf+margin+Heather+Meadows+cr.jpg | Blueberry leaf | Healthy | Blight_Spot | 0.9453 |
| vaccinium_angustifolium_leaf2.JPG.jpg | Blueberry leaf | Healthy | Blight_Spot | 0.6124 |
| prunsero_leaf1.jpg | Cherry leaf | Healthy | Blight_Spot | 0.5154 |
| prunsero_leaf2.jpg | Cherry leaf | Healthy | Blight_Spot | 0.5460 |
| three-vibrant-leaves-bird-cherry-tree-13905898.jpg | Cherry leaf | Healthy | Scab_Rot | 0.3591 |
| 02c.jpg | Corn leaf blight | Blight_Spot | Rust | 0.5929 |
| 0796.20graylssymt.jpg | Corn leaf blight | Blight_Spot | Rust | 0.7062 |
| 0c.jpg | Corn leaf blight | Blight_Spot | Healthy | 0.7013 |
| 1321189.jpg | Corn leaf blight | Blight_Spot | Rust | 0.5969 |
| 0796.39maizerust.jpg | Corn rust leaf | Rust | Blight_Spot | 0.8961 |
| 0796.40comrust.jpg | Corn rust leaf | Rust | Blight_Spot | 0.9999 |
| 0796.52srusttelia.jpg | Corn rust leaf | Rust | Blight_Spot | 1.0000 |
| 12-19striprustJIM.jpg | Corn rust leaf | Rust | Blight_Spot | 0.7116 |
| 1355.50commonrust.jpg | Corn rust leaf | Rust | Blight_Spot | 0.9955 |
| 2256-body-1501555581-1.jpg | Corn rust leaf | Rust | Blight_Spot | 0.7274 |
| 5496239405_d95bdb97d1_z.jpg | Corn rust leaf | Rust | Blight_Spot | 0.9990 |
| 80104747.jpg | Corn rust leaf | Rust | Blight_Spot | 0.9234 |
| P1130286.jpg | grape leaf | Healthy | Blight_Spot | 0.5315 |
| 03gb.jpg | grape leaf black rot | Scab_Rot | Blight_Spot | 0.9969 |
| 35589125035_662dd5b258_b.jpg | grape leaf black rot | Scab_Rot | Rust | 0.8001 |
| Black%20rot%20on%20foliage.jpg | grape leaf black rot | Scab_Rot | Blight_Spot | 0.6030 |
| Black%20rot%20on%20foliage2.jpg | grape leaf black rot | Scab_Rot | Healthy | 0.6642 |
| brleaf2_zoom.jpg | grape leaf black rot | Scab_Rot | Blight_Spot | 0.5630 |
| piano%20gully%20spray%20seed%20damage%2006%20%289%29.JPG.jpg | grape leaf black rot | Scab_Rot | Blight_Spot | 0.4555 |
| peach-leaf-isolated-white-background-42295220.jpg | Peach leaf | Healthy | Blight_Spot | 0.6037 |
| stock-photo-peach-leaf-isolated-on-white-background-281097503.jpg | Peach leaf | Healthy | Blight_Spot | 0.4942 |
| early-blight-alternaria-alternata-leaf-spotting-on-potato-leaf-X91XJE.jpg | Potato leaf early blight | Blight_Spot | Scab_Rot | 0.7626 |
| potato-early-blight-alternaria-alternata-lesion-on-a-potato-leaf-a1w1em.jpg | Potato leaf early blight | Blight_Spot | Rust | 0.7501 |
| depositphotos_1323264-Raspberry-leaf-on-white.jpg | Raspberry leaf | Healthy | Mosaic_Virus | 0.9338 |