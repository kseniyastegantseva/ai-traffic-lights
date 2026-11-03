# Возможное дополнение к PIERE после независимой проверки

## Что уже можно сообщить как development результат

В качестве отдельной абляции проверялось правило gap-out: после соблюдения минимальной
длительности зелёного переключать фазу, когда суммарная очередь текущей оси равна нулю,
противоположная очередь ненулевая, а время без наблюдаемой очереди достигает заданного порога.
Порог 1 с сравнивался с Queue-based Improved, Legacy и Vehicle-actuated в парном дизайне на
30 seed для каждого из восьми сценариев с горизонтом 1800 с.

При симметричном спросе 3 автомобиля/мин/подход среднее ожидание составило 4,26 с для gap-out,
5,27 с для Improved и 4,27 с для Vehicle-actuated. Средняя paired-разность gap-out минус
Improved равна −1,01 с (95% CI от −1,16 до −0,85; Holm-adjusted exact sign test p<0,0001 в
девятиконтрастной семье сценария). Разность относительно Vehicle-actuated равна −0,01 с
(95% CI от −0,05 до +0,03), то есть подтверждённого преимущества над этим baseline нет.

При 9 автомобилях/мин/подход gap-out показал 9,79 с против 9,16 с у Vehicle-actuated;
парная разность +0,63 с (95% CI от +0,38 до +0,88; Holm p=0,033). При 18 и 24 автомобилях/мин
gap-out не изменил метрики Improved в этом эксперименте, а Vehicle-actuated сохранил более
низкое среднее ожидание на 9,96 и 4,05 с соответственно.

## Ограничения формулировки

Это результат разработки алгоритма, а не независимый final test: после изучения таблицы seed
2101–2130 нельзя повторно использовать как закрытый тест для последующей настройки. Модель
определяет gap по секундному отсутствию наблюдаемой ожидающей очереди, а не по vehicle detector
headway или подтверждённому освобождению конфликтной зоны. При низкой нагрузке среднее ожидание
уменьшилось, но число переключений выросло примерно с 82 до 122 на 1800 с и суммарный жёлтый
вырос с 247 до 365 с; это важная цена изменения.

## Рекомендуемая формулировка для будущей версии статьи

«Exploratory paired development experiments suggest that an empty-axis gap-out rule can reduce
completed-vehicle mean waiting time relative to the congestion-aware queue-based controller
under symmetric low demand. However, the candidate did not outperform the vehicle-actuated
baseline in that regime and was significantly worse at 9 vehicles per minute per approach after
Holm correction. Under oversaturated demand the rule did not alter the improved controller's
operation. These findings are preliminary because the gap signal is an aggregate queue proxy and
the development seeds are not an independent final test.»

Эти данные пока не внесены в основную PIERE рукопись и не доказывают универсального преимущества
нового алгоритма.

## Capacity-boundary development screen

An additional paired development screen evaluated nine signal strategies at symmetric demands
from 9 to 18 vehicles per minute per approach. Each demand used 15 paired seeds; 1,800-second
and 3,600-second horizons were reported separately. At 3,600 seconds, Vehicle-actuated served
about 3,430 vehicles/hour at demand 16–18, while the mean residual queue increased from 79.8
vehicles at demand 14 to 216.1 at 15 and 881.8 at 18. This suggests overload in the region
around 14–15 vehicles/minute/approach for this model, but does not establish a stationary
capacity threshold.

The mean waiting time for Queue-based Improved was 383.00 s at demand 18, compared with 371.32 s
for Vehicle-actuated (paired difference +11.68 s, 95% CI [+9.35, +14.01], Holm-adjusted p=0.0022
within the demand-by-metric family of 36 contrasts). Improved also had higher wait at 14–17 after
Holm correction; at 12 and 13 the corrected evidence did not establish a difference. Empty-gap
1 s closely tracked Improved and did not remove its disadvantage to Vehicle-actuated. Results
are exploratory: there were 15 development seed pairs, and the 3,600-second series reused the
same seed IDs and 1,800-second arrival prefixes. Independent seeds and longer horizons are
needed around 13–15 vehicles/minute/approach.

This paragraph is a candidate for later author review; the main six-page PIERE manuscript remains
unchanged. Full per-controller tables and audit artifacts are in `outputs/total_improvement/`.
