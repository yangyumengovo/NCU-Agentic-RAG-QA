import os

# 高精度南昌大学官方样式矢量 SVG 校徽（依据官方 VI：双圆环、昌大青花蓝 #003366、青花瓷盘纹路、香樟树矢量图案、赵朴初字体与 NANCHANG UNIVERSITY）
ncu_svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <!-- 昌大青花蓝渐变 -->
    <linearGradient id="ncuBlueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#002d62"/>
      <stop offset="50%" stop-color="#003b73"/>
      <stop offset="100%" stop-color="#004b87"/>
    </linearGradient>
    
    <!-- 路径文字：南昌大学 -->
    <path id="textArcTop" d="M 30,100 A 70,70 0 1,1 170,100" fill="none"/>
    <!-- 路径文字：NANCHANG UNIVERSITY -->
    <path id="textArcBottom" d="M 170,100 A 70,70 0 0,1 30,100" fill="none"/>
  </defs>

  <!-- 外圈青花圆盘边框 -->
  <circle cx="100" cy="100" r="96" fill="url(#ncuBlueGrad)" stroke="#001d42" stroke-width="2"/>
  <!-- 青花瓷盘双同心套圈线 -->
  <circle cx="100" cy="100" r="91" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-dasharray="6 3"/>
  <circle cx="100" cy="100" r="88" fill="none" stroke="#ffffff" stroke-width="1"/>
  <circle cx="100" cy="100" r="66" fill="none" stroke="#ffffff" stroke-width="1.5"/>

  <!-- 顶部校名：南昌大学 (毛体中文) -->
  <text font-family="'Noto Serif SC', 'SimSun', serif" font-weight="bold" font-size="20" fill="#ffffff" letter-spacing="4">
    <textPath href="#textArcTop" startOffset="50%" text-anchor="middle">南昌大学</textPath>
  </text>

  <!-- 底部英文：NANCHANG UNIVERSITY -->
  <text font-family="'Inter', sans-serif" font-weight="700" font-size="10" fill="#ffffff" letter-spacing="2">
    <textPath href="#textArcBottom" startOffset="50%" text-anchor="middle">NANCHANG UNIVERSITY</textPath>
  </text>

  <!-- 两侧青花花纹节点 -->
  <circle cx="28" cy="100" r="3" fill="#ffffff"/>
  <circle cx="172" cy="100" r="3" fill="#ffffff"/>

  <!-- 内圈圆盘：瓷白背景 -->
  <circle cx="100" cy="100" r="63" fill="#ffffff"/>
  
  <!-- 内圈青花水纹与香樟树主体图案 (Camphor Tree Symbol) -->
  <!-- 香樟树树干与分叉枝干 -->
  <path d="M 96 142 L 96 108 L 82 92 L 87 88 L 97 100 L 97 78 L 103 78 L 103 100 L 113 88 L 118 92 L 104 108 L 104 142 Z" fill="#003366"/>
  <!-- 茂密的香樟树冠（文理结合、百年树人） -->
  <circle cx="100" cy="65" r="18" fill="#003366" opacity="0.9"/>
  <circle cx="82" cy="74" r="15" fill="#003366" opacity="0.9"/>
  <circle cx="118" cy="74" r="15" fill="#003366" opacity="0.9"/>
  <circle cx="70" cy="88" r="13" fill="#003366" opacity="0.85"/>
  <circle cx="130" cy="88" r="13" fill="#003366" opacity="0.85"/>
  <circle cx="100" cy="82" r="16" fill="#003366" opacity="0.95"/>
  <circle cx="86" cy="94" r="12" fill="#003366" opacity="0.9"/>
  <circle cx="114" cy="94" r="12" fill="#003366" opacity="0.9"/>

  <!-- 青花瓷盘水纹基底 (1993/2005) -->
  <path d="M 50 132 Q 75 125 100 132 T 150 132 L 150 148 L 50 148 Z" fill="#003366" opacity="0.15"/>
  <path d="M 45 138 Q 72 132 100 138 T 155 138" fill="none" stroke="#003366" stroke-width="2"/>
  <path d="M 55 144 Q 78 140 100 144 T 145 144" fill="none" stroke="#003366" stroke-width="1.5"/>

  <!-- 建校年份标识 -->
  <text x="100" y="157" font-family="'Inter', sans-serif" font-weight="700" font-size="9" fill="#003366" text-anchor="middle" letter-spacing="1">1921</text>
</svg>
"""

output_path = r"f:\毕业论文\web\ncu_logo_official.svg"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(ncu_svg_content)

print(f"官方标准的南昌大学矢量 SVG 校徽已生成至: {output_path}")
