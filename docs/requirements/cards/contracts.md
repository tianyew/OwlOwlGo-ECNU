# 本轮卡片共用接口与数据约定

**2026-11-17模型调用范围确认：** 团队统一购买API；黄云舒负责N03计划说明/调整理由，周子涵负责N04小鸮生成，郑仲佑负责N09候选题生成并接Q-E审核。每位负责人完成自己的后端调用、提示词、校验和失败处理，不新增公共模型调用基础任务，不给管佳欣新增模型平台职责。密钥使用服务端配置，不发送到前端。

**2026-11-17题库扩展：** 新测验以[题库接口与数据约定](question-bank.md)为准，采用测验实例、类型化答案与动态题量。下方K02—K04描述旧接口/历史兼容行为，8/2/10题与原阈值不作为新题库验收要求；新接口/规则必须支持审核后的批量题目。N02/N06/N07补充实例、HSK标准版本、范围和题目快照。

日期：2026-11-16。**K开头为本次已核对的现有接口；N开头均为本轮建议新增/扩展契约，尚未实现。** 本文把页面卡片的接口选择写具体，避免五人分别设计不兼容接口。实现中如需变更，先同步契约、调用卡片和测试，不静默改语义。数据库技术步骤见[迁移计划](../../software/postgresql-integration-plan.md)。

## 0. 公共约定

- 路径前缀：账号`/api/v1/auth`，学习`/api/v1/learning`。本文件中的相对路径按所在表指定前缀补全。
- 身份使用现有HttpOnly Cookie；请求使用`credentials: same-origin`。不接受客户端指定user_id、分数、完成标记或权限。写请求保留现有同源检查。
- 新接口成功对象按以下字段返回；新接口错误使用`{detail: string, code: string}`。401未登录；404不存在或不属于本人；409版本/幂等内容冲突；422字段或流程不合法；503服务不可用。现有接口的`detail:string`仍须兼容，前端错误解析不能要求所有旧接口都有code。
- 新的ID使用UUID字符串；内容单元ID沿用`travel-0`等，quiz_id沿用`assessment`、`unit-travel-0`、`post-travel`。全部时间ISO 8601 UTC；显示时转换本地时间。
- request_id/event_id/submission_id在一次动作首次发送前生成；网络未知结果重试保持原ID与相同请求体，用户明确开始新动作才生成新ID。唯一约束按用户隔离；同ID不同内容409。
- **保存策略**：前测/测验草稿沿用串行保存队列；设置页显式保存或点生成时先保存；计划接受和正式测验属于明确提交。页面切换不自行标记课程完成。各模块revision/version独立，不互相用旧整包覆盖。
- 新接口均在真实PostgreSQL上验收。当前JSON的数据状态见[现状](../implementation-status.md)；这里写表字段不表示已经建表。

## K01 账号（现有）

| 方法/路径（auth前缀） | 请求 | 成功结果 | 页面 |
| --- | --- | --- | --- |
| GET /me | 无 | 200 `{id,username,display_name}`；未登录401 | 现有公共导航/保存条、F01/F02 |
| POST /register | `{username,password,display_name}`；确认密码仅前端 | 201同上并建立Cookie会话；重名409 | F01/F02 |
| POST /login | `{username,password}` | 200用户与Cookie；错误凭据401 | F01/F02 |
| POST /logout | `{}` | 204；清除会话与Cookie | 现有公共导航/保存条 |

用户名归一化为去首尾空格、小写，3—32个字母/数字/下划线；注册密码8—128；登录密码1—128；昵称去空白后1—40字符。邮箱注册/忘记密码/改密码不在本轮。

## K02 课程（现有，元数据扩展见N08）

`GET /curriculum`无需登录，返回`{content_version,topics:[{id,title,english,description,schedule,posttest_id,units:[{id,title,goal,words,grammar,example,dialogue,practices,task,quiz_id}]}]}`。四个topic_id为travel/daily/campus/poetry；每方向5单元。公开结果不能含答案。

## K03 草稿与正式进度（现有）

- `GET /progress`返回`{revision,state,updated_at,analysis,results,profile,topic_completion}`，results按quiz_id索引最新正式结果。
- `PUT /progress`请求`{revision,state}`；state现有字段为`content_version,onboarding_complete,stage,quiz,topic,completed,checks,posttests,drafts`。必须基于最近服务端快照编辑；不要随意塞入新偏好/计划字段，当前schema禁止额外字段。
- 草稿：`drafts[quiz_id]={content_version,current,answers:[{question_id,selected_index}]}`；current为0起始页码。完整LearningState沿用现有类型和校验，正式分数与completed由服务端重新推导。
- 409停止自动重试，保留本地草稿供用户查看，显示“另一页面已更新，请重新加载”；重新加载前提示可能放弃未保存修改。已保存和未保存状态必须区分。

## K04 旧测验与提交（历史兼容；新卷改用实例接口）

- `GET /quizzes/{quiz_id}`公开题目及`result,draft,unit_completed`；游客的个人结果为空。问题有id/prompt/options/category等，不含answer/explanation。
- `POST /quizzes/{quiz_id}/submissions`：`{submission_id,content_version,revision,answers:[{question_id,selected_index}]}`；200返回`{result,progress}`，result含submission_id/quiz_id/kind/topic/unit_index/content_version/scoring_version/created_at/score/correct/total/passed/items。
- items为已提交题目的判分及解析快照；未提交时不下发正确答案。每题恰好一次、选项索引合法、所有题答齐，服务端统一判分。
- 前测8题不设及格门槛；单元2题全部正确才通过；后测10题≥60分通过；方向完成为5单元均曾通过且本方向后测曾通过。通过后重练失败不撤销完成。
- 原ID同内容重试返回原结果；同ID换答案/测验409；未完成前测或方向不匹配422；无登录401。
- 本轮SQL中由服务端在正式提交快照关联当时生效plan_id/version（前测为空；旧数据可为空），不让浏览器提交任意计划归属。接受计划与提交同用progress revision协调并发。

## K05 重新前测（现有）

`POST /assessment/reset`请求`{revision}`，返回新progress。增加epoch，清当前前测与方向设置状态、当前AI分析；保留旧正式提交、画像证据与已通过单元。旧plan保留为历史/待重新规划，不可跳过新前测直接获得正式提交权限。前端先弹明确确认，再调用；失败不清本地已成功结果。

## K06 当前AI分析（现有兼容入口）

`POST /analysis`请求`{}`；读取当前已提交前测，返回已有Analysis结构。旧行为无Key/故障503。B新增N02后，页面改用绑定diagnosis_id的分析接口；保留此入口兼容既有调用，可委托同一服务，不再维护两套反馈逻辑。

## N01 目标与时间设置（新增，黄云舒）

- `GET /preferences` → `{version:0|int,goal:string,self_reported_level:'unknown'|'beginner'|'basic'|'intermediate',daily_minutes:int|null}`；未设置返回version=0、空目标、unknown、null，不伪装已保存。
- `PUT /preferences`请求上述四业务字段+version；goal去空白后1—200字符，daily_minutes必须整数10—120，枚举之外422。首次version=0成功返回version=1，以后每次成功更新+1；旧版本409。
- 表：learning_preferences(user_id唯一,version,goal,self_reported_level,daily_minutes,updated_at)。自报水平不能覆盖测评结果。主动提示开关由N05独立维护。

## N02 诊断快照与反馈（新增，钱俊）

- 每次**成功正式前测提交**，在同一业务事务写唯一诊断快照；唯一键(user_id,submission_id)。诊断包含`diagnosis_id,submission_id,assessment_epoch,created_at,content_version,scoring_version,diagnosis_rule_version,scope,score,dimensions,evidence_status,rule_feedback`。dimensions用明确name/total/correct，未测维度不填0分。
- `GET /diagnoses/current` → `{diagnosis:Diagnosis|null}`，仅当前epoch；`GET /diagnoses?offset=0&limit=20` → `{items:[DiagnosisSummary],next_offset:int|null}`，按created_at与ID倒序稳定排序，limit为1—50。
- `GET /diagnoses/{id}` → `{diagnosis,analysis:AnalysisEnvelope|null}`，只读本人历史；不在读取时自动调用模型。
- `POST /diagnoses/{id}/analysis`请求`{}` → `{diagnosis_id,status:'ready'|'fallback',source:'ai'|'rule',feedback:Analysis,generated_at,prompt_version,model:string|null}`。无Key、超时或校验不通过时200返回规则反馈并标fallback，不用AI标签冒充；服务自身无法读取数据则503。
- Analysis继续沿用summary/strengths/focus_areas/question_feedback/practice_tasks/next_steps字段；规则反馈同样按实际题目生成，全对不编造错题。仅分析当前诊断；旧诊断POST返回409，历史GET仍可读已存分析。
- AI结果按诊断ID+证据指纹+prompt_version缓存/追加，不修改不可变诊断证据。页面只接收自己正在查看的diagnosis_id结果。重测期间原请求返回不能写当前分析；旧请求可丢弃或只附到原历史快照。
- 迁移时为可核验的历史正式前测幂等补诊断，标明来源及是否为回填，不捏造历史AI分析。legacy_answers不成为新的可信画像证据。

## N03 候选与生效计划（新增，黄云舒）

- `GET /plans/current` → `{plan:Plan|null,requires_replanning:boolean}`；没有计划为null。
- `POST /plans/proposals`请求`{request_id,topic_id,diagnosis_id,preferences_version,base_plan_version}`。base_plan_version无生效计划时0；校验当前诊断、偏好和用户归属后生成候选。候选不修改state.topic或当前计划。
- Plan字段：`plan_id,version:int|null,status:'candidate'|'accepted',topic_id,goal,daily_minutes,source_versions,days,units,diff,created_at,accepted_at:null|string`。source_versions含diagnosis_id/epoch/preferences_version/catalog_version/policy_version/base_plan_version/evidence_fingerprint；fingerprint由服务端正式证据计算，草稿变动不改变其含义。
- units逐项含`unit_id,content_version,title,goal,duration_minutes,prerequisite_ids,reason,completion_rule`；days为`[{day_index:1,unit_ids:[...],total_minutes:int}]`。已完成单元显示状态但不重复安排为必学；其先修视为满足。未完成单元按先修稳定拓扑排序，同级按原课程顺序，逐日顺序装入预算。
- 单元不能任意拆分；候选题目不新增；无合格内容/循环先修/预算容不下最小单元返回422及明确code，不虚构安排。预估时长缺失或未审核不能选入。
- `POST /plans/{id}/accept`请求`{request_id,base_plan_version,revision}`；事务重验候选输入版本和正式证据指纹、progress revision，成功分配递增计划version、使唯一计划生效、更新state.topic/stage/onboarding_complete，返回`{plan,progress}`。失败保持原计划。相同接受请求重放返回原结果，不创建新版本。
- `GET /plans/{id}`读本人候选/历史。取消预览仅丢弃本地candidate_id并返回，不调用accept，不取消已有生效计划。非本轮范围不做异步队列/取消后台任务。
- 新偏好、诊断或正式证据改变后接受旧候选返回409；浏览旧生效计划不丢历史成果。生成失败仍允许查看旧计划。
- 兼容旧原型：C迁移已有topic/onboarding_complete为明确标注`legacy-preset-v0`的计划快照，保留原顺序，不冒称个性化；新规则计划须显式接受。重测后requires_replanning=true，完成新诊断并接受新计划才回到完整新流程。

### N03补充：计划说明与调整理由（黄云舒）

- 合法候选创建后，前端自动请求`POST /plans/{id}/explanation`，请求`{request_id}`；后端读取本人候选、诊断/偏好/课程快照和旧计划diff，不接受浏览器编造证据。GET计划返回已保存的explanation，刷新不自动重复生成。
- 返回`{plan_id,input_fingerprint,status:'ready'|'fallback',source:'ai'|'rule',summary,unit_reasons:[{unit_id,text,evidence_ids}],change_reasons:[{change_id,text}],model:null|string,prompt_version,generated_at}`。初次计划change_reasons为空；改计划只引用程序生成的change_id。
- 输入包含目标/每日预算、已测证据范围、真实课程/先修/时长、候选及旧计划差异。模型只输出文字说明；不可修改计划内容、评分或完成状态。结构/引用校验与越界能力断言检查失败，回退真实规则说明，不能仅检查JSON就算通过。
- 第一次生成中页面显示“正在生成说明”；超时/限流/额度不足/内容校验失败时返回200 fallback并可手动重试。存储/身份错误按常规错误处理，不伪装模型回退。合法计划可在说明失败时接受。
- 同用户同request_id同输入返回原结果，异输入409；生成期间相同请求返回202处理中，可用GET计划查询，不重复发起供应商调用。手动“重试说明”在已确认fallback后用新request_id；未知结果重放原ID。迟到响应不得覆盖更晚一次说明或新候选。
- 调用外部API不持有计划接受事务；保存前重验候选归属、输入指纹和说明请求序号。候选已过时返回409；接受计划只使用已存结果，不触发新模型调用。说明记录关联模型和提示词版本。

## N04 独立练习与提示事件（新增，周子涵）

- `POST /practice-sessions`请求`{request_id,unit_id,content_version}`；仅本人当前方向旅游首单元、已完成前测可创建；返回PracticeSession。未开放单元422；不能传assessment/post测验ID取提示。
- PracticeSession包含`session_id,unit_id,content_version,revision,status:'active'|'paused',current_question_id,questions:[PublicQuestion],question_states,updated_at`。question_states按题ID给attempt_count/hint_level/last_is_correct/last_feedback；公开题不含答案。
- `GET /practice-sessions/current?unit_id=travel-0` → `{session:null|PracticeSession}`；`GET /practice-sessions/{id}`返回本人会话。刷新先读取已保存会话；不以打开面板重复创建新练习。
- `POST /practice-sessions/{id}/events`请求`{event_id,revision,question_id,action:'answer'|'hint'|'explain'|'example'|'scenario'|'select_question'|'pause',selected_index?:int}`。answer才允许selected_index，其他动作禁止带答案。题目必须属于绑定内容；success返回`{event_id,session,feedback:{text,level,source:'ai'|'template',reason,policy_version,model:null|string,prompt_version,content_kind:'hint'|'explanation'|'example'|'scenario'}|null}`。
- 每题初始level0；首次错误记录level1，界面只做必要正误/再试反馈；hint在未用帮助时返回2，再次hint到3，停留3不自动给4；explain须用户明确请求才到4。已经较高级别不能被答错自动降级。同题事件重放不重复升级或计尝试。
- 连续两错且主动提示开启只显示“需要一点提示吗？”邀请；关闭则不出现未请求教学提示，主动hint/explain仍可用。不可仅按停留时间触发帮助。
- hint/explain/example/scenario由后端按课程/题目版本、用户实际错误、必要历史和允许级别调用统一购买的API；0/1基础反馈无需调用模型。模型不得决定自己的帮助级别。结构、引用、课程相关性与答案泄露校验通过才显示source=ai。
- API无配置/超时/限流/额度不足或内容校验失败时，使用B提供、E复核且与题目版本/动作/级别一致的备用模板，标source=template。无合格备用内容返回503 `hint_unavailable`，不提交成功事件、不升级；用户可继续作答。数据库和身份失败不能转成模板成功。
- example/scenario用于即时不计分学习材料，不改变hint_level，不入正式题库，不调用评分/进度更新。例句要求词汇/句型和解释；情境要求角色、场景和任务。两种动作仍检查不得泄露当前受保护题答案；需要正式入库时由内容成员通过N09候选审核入口处理。
- 请求先登记用户/事件ID和输入指纹；相同事件处理中返回202，GET会话可查询pending_event与状态，不能重发供应商请求。外部调用结束后，在短事务中重验会话revision/题目上下文并保存事件、反馈及级别；过时返回409，不污染新题。供应商调用失败记录可保留，但不作为成功教学事件。
- 成功AI或模板事件重放返回原反馈；已明确失败且没有反馈时同ID允许重新执行，成功最多提交一次。模板成功后不自动补调用模型；用户下一次明确生成使用新事件ID。不得承诺网络不确定时外部供应商绝不重复计费。
- 事件、状态、revision在同一事务保存；记录服务端输入快照、action、reason、confidence（若为规则值需说明）、policy_version。练习表与正式submissions分离，不调用正式判分完成更新。
- 正式前测、正式单元小测与后测活动中禁止解题生成；不能通过改会话ID调用独立练习接口绕过限制。退出关闭面板不会删除已保存会话；pause失败保留已确认记录并显示未确认。切换题目以服务端成功结果为准，防止不同题目的hint_level串用。

## N05 主动提示设置（新增，周子涵）

`GET /intervention-preferences` → `{version:0|int,proactive_hints:boolean}`，默认false；`PUT /intervention-preferences`请求同结构，成功version+1，旧版本409。只改独立设置表，不覆盖N01学习目标。失败时开关回到服务端已确认值并显示重试。

## N06 错题复习（新增，郑仲佑）

`GET /review-queue` → `{policy_version:'latest-wrong-v1',generated_at,items:[{source_question_id,submission_id,question_id,quiz_id,unit_id:string|null,topic_id:string|null,prompt,options,selected_index,correct_index,explanation,reason,last_submitted_at,practice_available:boolean}]}`。

仅本人正式记录且provenance不是legacy_answers；按每个source_question_id的最新正式结果筛仍错误题，去重后按时间倒序、同时间来源ID排序，最多10题。关联字段由服务端映射，不从浏览器猜unit_id。前测错题无对应单元时unit_id=null，显示原前测解析，不制造课程跳转；practice_available仅旅游试点且满足当前方向/前测条件时true。浏览列表/详情不写成绩。跨方向课程可只读预览；正式练习前必须显式变更方向与接受计划，不能在“复习”点击中暗改计划。

## N07 指定正式结果与画像（结果读取新增，郑仲佑；判分仍用K04）

`GET /submissions/{submission_id}` → `{result:QuizResult,topic_completion:boolean,completed_units:int,profile:LearnerProfile}`，只读本人结果。F15报告只接受kind=posttest；错误类型422/前端回对应页。报告得分绑定指定提交，完成数与画像为查询时当前累计值，页面分别标明“本次后测”和“当前累计记录”。

`GET /profile`现有K接口维持规则：去重首次证据、最近表现、数量型confidence、0题null、1题不足、2—4初步、5及以上较多；独立练习不计入。

## N08 课程审核与模板资产（内容扩展，郑仲佑主责，钱俊提供模板）

版本化内容清单新增`unit_id,content_version,duration_minutes,prerequisite_ids,difficulty_note,source,license_note,review_status:'pending'|'approved'|'disabled',reviewer,reviewed_at`。记录审核人实际身份，无法核实保持pending。新规划只用approved且来源/时长/先修完整的条目；历史引用版本不原地改写。模板另记录question_id/content_version/hint_level/text/template_version/review_status及禁止泄露反例。

公开课程可继续只读展示现有内容，但要标明未审核内容不进入新规则计划；未审核条目不能宣称“已审核”。首次只验收旅游试点可用，全20单元均有明确审核或待审核状态，不要求虚构全部审核完成。

## N09 AI生成候选题（新增，郑仲佑）

管理前缀`/api/v1/content`。复用Q-A内容角色与Q-E审核权限，普通学习者不可调用或读取生成答案。

- `POST /question-generations`请求`{request_id,standard_id,level,skill,question_type,knowledge_points,syllabus_references,difficulty,length_constraints,count,topic_ids?,unit_ids?}` →202 `{generation_id,status:'pending'}`。等级/题型/考点须来自团队已登记标准；count为正整数且不超过服务端配置的本批上限。团队尚未确定的等级和题量不能由接口默认决定。
- 服务端读取标准条目上下文，按请求约束调用购买的模型API；保存作者/请求人、约束快照、model/prompt_version及生成状态。生成器自身的“符合HSK”声明不能代替审核。
- `GET /question-generations/{id}` → `{generation_id,status:'pending'|'running'|'completed'|'partial'|'failed',requested_count,generated_count,valid_count,candidates:[{candidate_id,version,question,validation_errors,review_status:'draft'}],failure_reason}`。仅有权内容成员可读；格式失败保留诊断信息，不创建可发布题；部分成功只报告实际数量。
- 候选question遵循题库字段约定，至少含题干、类型化选项/答案、解析、考点依据、素材需求及source='ai_generated'。缺素材、疑似重复、答案不一致或无效依据的候选不可送审。格式合法不等于内容正确。
- `PATCH /question-candidates/{id}`请求`{expected_version,question}`编辑本人候选；写入新修订并重新校验。`POST /question-candidates/{id}/submit-review`请求`{request_id,expected_version}`仅允许机器校验无阻塞问题、素材齐全的版本，幂等转Q-E待审，关联原generation_id。
- `DELETE /question-candidates/{id}`仅丢弃尚未送审的本人草稿，保留批次审计；待审/已发布内容走Q-E退回/停用流程。生成者/编辑作者集合不能审核该题，钱俊提供标准支持并参与非作者审核。
- 同request_id同约束返回同generation_id，异约束409；重复点击不创建新批。失败后用户明确“重新生成”使用新ID，不自动循环付费。供应商错误向页面返回可理解原因，不回显密钥/原始响应。
- 只有Q-E非作者审核通过且素材完整后，发布者显式发布；候选不计有效题量，不参与新卷，不自动补足上传题库的内容指标。上传题和AI题使用同一发布门禁。

## 依赖与事务收口

A提供数据库连接、核心账户/学习仓储和统一事务边界；B提供写诊断函数及迁移，由A的正式前测事务调用，不由B另起已提交事务。C接受计划更新计划与progress必须同事务；D练习事件独立事务；E查询不修改正式成绩。Alembic修订按PR顺序形成可升级链。

合约fixture最少包含：未登录、全新账号、前测草稿、正式诊断、AI回退、候选计划、生效计划、过时版本、部分完成、后测结果、空画像、重复错题、提示2级与4级、跨用户请求。API样例需使用虚构账号，不带真实Cookie/密钥。
