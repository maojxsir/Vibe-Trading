// Curated seed for the 新闻 (news) page.

export interface NewsItem {
  source: string;
  time: string;
  title: string;
  summary: string;
  tickers: string[];
}

export const newsSeed: NewsItem[] = [
  {
    source: "财联社",
    time: "2026-06-03 16:42",
    title: "光模块需求能见度延伸至 2027，龙头订单饱满",
    summary: "多家机构上修光模块需求，800G 放量、1.6T 送样推进，CPO 路线进展密集。",
    tickers: ["中际旭创", "天孚通信"],
  },
  {
    source: "证券时报",
    time: "2026-06-03 14:10",
    title: "人形机器人量产节奏加快，核心零部件国产替代提速",
    summary: "减速器、丝杠、力矩传感器国产突破，整机降本路径逐步清晰。",
    tickers: ["绿的谐波", "双环传动", "拓普集团"],
  },
  {
    source: "上证报",
    time: "2026-06-03 10:25",
    title: "高端 PCB 供不应求，覆铜板涨价传导至下游",
    summary: "AI 服务器单机 PCB 价值量提升，头部厂商产能爬坡盈利弹性大。",
    tickers: ["沪电股份", "胜宏科技"],
  },
  {
    source: "第一财经",
    time: "2026-06-02 21:08",
    title: "国产 GPU 推理侧加速落地，生态与互联成关键",
    summary: "寒武纪、海光信息推理场景渗透，自主可控政策持续催化。",
    tickers: ["寒武纪", "海光信息"],
  },
];
