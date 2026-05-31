import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

/** Display name for a profile district (values in DB stay Russian). */
export function useDistrictLabel() {
  const { t, i18n } = useTranslation();

  return useCallback(
    (ruName) => {
      if (!ruName || i18n.language !== 'alt') return ruName;
      return t(`districts.${ruName}`, { defaultValue: ruName });
    },
    [t, i18n.language],
  );
}
