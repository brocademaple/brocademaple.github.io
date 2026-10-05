import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'output/gallery/master-v2-polish/artworks.json'
d=json.loads(p.read_text())
titles={
'art-deco-poster-purple-peacock-gold-lines':'孔雀金线','ceramic-vase-cobalt-blue-gold-leaf':'钴蓝与金箔','dark-reading-room-aubergine-olive-brass':'暮色阅览室','luxury-poster-midnight-blue-antique-gold':'午夜蓝金','minimal-product-misty-blue-matte-gold':'雾蓝静物','mysterious-portrait-deep-purple-emerald-gold':'翡翠幽影','quiet-still-life-smoky-purple-sage-muted-gold':'烟紫与鼠尾草','refined-product-navy-blue-champagne-gold':'香槟蓝调',
'arched-doorway-frame':'门后的光','asymmetric-two-person':'两个人的距离','asymmetrical-balance-poster':'不对称平衡','close-up-crop':'局部肖像','diagonal-motion':'斜向的动势','diagonal-still-life':'倾斜的静物','edge-negative-space':'边缘留白','foreground-obstruction':'前景之后',
'candlelit-dinner-still-life':'烛光静物','colored-gel-portrait':'彩光肖像','dappled-sunlit-interior':'树影入室','dramatic-side-light-portrait':'侧光之间','golden-hour-backlit-portrait':'金色逆光','high-key-beauty-portrait':'柔白肖像','low-key-chiaroscuro-perfume':'暗处的香气','neon-rim-rainy-street':'雨夜霓虹',
'black-leather-handbag':'黑色皮革','brushed-metal-watch':'拉丝金属','cobalt-ceramic-bowl':'钴蓝陶碗','embroidered-silk-pouch':'丝绣','frosted-glass-perfume':'磨砂之香','handmade-paper-stationery':'纸的肌理','iridescent-foil-cosmetic':'虹彩箔光','marble-tray':'大理石纹',
'detached-elegance':'疏离的优雅','determined-sharp-gaze':'坚定凝视','dreamy-nostalgia':'旧梦','mysterious-ethereal':'空灵之境','peaceful-healing':'安宁','playful-sly-expression':'狡黠一瞬','quiet-confidence':'安静的自信','rainy-window-melancholy':'雨窗',
'art-book-magazine':'书页之间','black-cherry-tart':'黑樱桃','ceramic-vase-interior':'室内花器','gift-box-packaging':'礼物','jewelry-black-velvet':'黑丝绒上的珠宝','luxury-bag-accessory':'随身之物','perfume-blue-gold':'蓝金香氛','scented-candle-amber':'琥珀烛光'}
for a in d:
 a['titleZh']=next((v for k,v in titles.items() if k in a['id']),a['title'])
p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
