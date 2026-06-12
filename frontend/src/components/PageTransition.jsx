import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { COMPACT_GAME_QUERY, PAGE_TRANSITION_DURATION } from '../constants';
import useMediaQuery from '../hooks/useMediaQuery';

export default function PageTransition({ children }) {
  const location = useLocation();
  const compactLayout = useMediaQuery(COMPACT_GAME_QUERY);
  const [displayChildren, setDisplayChildren] = useState(children);
  const [transitionStage, setTransitionStage] = useState('enter');
  const prevPathRef = useRef(location.pathname);

  useEffect(() => {
    if (compactLayout) {
      setDisplayChildren(children);
      prevPathRef.current = location.pathname;
      setTransitionStage('enter');
      return undefined;
    }

    if (location.pathname !== prevPathRef.current) {
      setTransitionStage('exit');
      const timeout = setTimeout(() => {
        setDisplayChildren(children);
        prevPathRef.current = location.pathname;
        setTransitionStage('enter');
      }, PAGE_TRANSITION_DURATION);
      return () => clearTimeout(timeout);
    }
    setDisplayChildren(children);
    return undefined;
  }, [children, location.pathname, compactLayout]);

  if (compactLayout) {
    return (
      <div className="page-transition" style={{ width: '100%', height: '100%' }}>
        {children}
      </div>
    );
  }

  return (
    <div
      className={`page-transition page-${transitionStage}`}
      style={{
        opacity: transitionStage === 'enter' ? 1 : 0,
        transform: transitionStage === 'enter' ? 'translateY(0)' : 'translateY(10px)',
        transition: `opacity ${PAGE_TRANSITION_DURATION}ms ease-out, transform ${PAGE_TRANSITION_DURATION}ms ease-out`,
        width: '100%',
        height: '100%',
      }}
    >
      {displayChildren}
    </div>
  );
}
