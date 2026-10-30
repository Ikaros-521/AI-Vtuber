/** 玩法库工作区：20+ 可选玩法的开关卡片（直播互动 / 自动运营 / 进阶联动）。

 * 区块本体定义在 interaction.ts / hardware.ts / brain.ts（多模态部分），
 * 这里只做分组组装——答谢类文案归「弹幕管家」，不在这里重复出现。
 */
import type { Workspace } from '../types'
import {
  chooseSongSection,
  integralSection,
  sdSection,
  copywritingSection,
  scheduleSection,
  idleTimeTaskSection,
  trendsConfigSection,
  searchOnlineSection,
  trendsCopywritingSection,
} from './interaction'
import {
  keyMappingSection,
  customCmdSection,
  luoxiSection,
  coordinationSection,
  serialSection,
} from './hardware'
import { imageRecognitionSection, translateSection } from './brain'

export const playWorkspace: Workspace = {
  id: 'play',
  title: '玩法库',
  groups: [
    {
      title: '直播互动',
      sections: [chooseSongSection, integralSection, sdSection],
    },
    {
      title: '自动运营',
      sections: [idleTimeTaskSection, scheduleSection, copywritingSection, trendsCopywritingSection, trendsConfigSection],
    },
    {
      title: '进阶联动',
      sections: [
        keyMappingSection,
        customCmdSection,
        luoxiSection,
        coordinationSection,
        serialSection,
        searchOnlineSection,
        translateSection,
        imageRecognitionSection,
      ],
    },
  ],
}
